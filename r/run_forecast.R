# Does the central bank mood index improve macro forecasts?
#
# Usage (from the repository root):
#   Rscript r/run_forecast.R            # uses cached macro data if present
#   Rscript r/run_forecast.R --refresh  # re-download from BIS and OECD
#
# Reads  data/index/mood_index.csv (from `python -m mood_tracker.mood_index`)
# Writes results/forecast_results.csv and results/forecast_results.md

source("r/R/fetch_macro.R")
source("r/R/forecast_eval.R")

args <- commandArgs(trailingOnly = TRUE)
refresh <- "--refresh" %in% args

RATE_HORIZON <- 3   # months ahead for the policy-rate change
RATE_TRAIN   <- 36  # months before the first forecast
GDP_TRAIN    <- 16  # quarters before the first forecast

index_path <- "data/index/mood_index.csv"
if (!file.exists(index_path)) {
  stop("No mood index found; run `python -m mood_tracker.mood_index` first.")
}
index <- utils::read.csv(index_path, stringsAsFactors = FALSE)
countries <- sort(unique(index$country))
message("Mood index: ", nrow(index), " country-months for ",
        paste(countries, collapse = ", "))

# Fetch (or read from cache) every supported country, then keep the indexed ones.
rates <- fetch_policy_rates(COUNTRY_CODES$country, refresh = refresh)
gdp   <- fetch_gdp_growth(COUNTRY_CODES$country, refresh = refresh)
rates <- rates[rates$country %in% countries, ]
gdp   <- gdp[gdp$country %in% countries, ]

rate_panel <- build_rate_panel(index, rates, horizon = RATE_HORIZON)
gdp_panel  <- build_gdp_panel(index, gdp)

results <- rbind(
  evaluate_panel(rate_panel, "policy rate, 3 months ahead",
                 min_train = RATE_TRAIN, horizon = RATE_HORIZON),
  evaluate_panel(gdp_panel, "GDP growth, next quarter",
                 min_train = GDP_TRAIN, horizon = 1)
)

dir.create("results", showWarnings = FALSE)
if (is.null(results) || nrow(results) == 0) {
  message("\nNo country has enough months of mood index overlapping the macro data ",
          "to run the test.\nScore more history first, for example:\n",
          "  python -m mood_tracker.score --countries US EA GB JP CA --start 2005 --per-month 5")
  quit(status = 0)
}

results$verdict <- ifelse(
  is.na(results$dm_p_value), "test not defined",
  ifelse(results$rmse_ratio < 1 & results$dm_p_value < 0.10,
         "mood index helps",
         ifelse(results$rmse_ratio > 1 & results$dm_p_value < 0.10,
                "mood index hurts", "no significant difference")))

utils::write.csv(results, "results/forecast_results.csv", row.names = FALSE)

fmt <- function(x, digits) formatC(x, format = "f", digits = digits)
table_lines <- c(
  "| Exercise | Country | Forecasts | RMSE benchmark | RMSE with mood | Ratio | DM p-value | Verdict |",
  "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
  sprintf("| %s | %s | %d | %s | %s | %s | %s | %s |",
          results$exercise, results$country, results$n_forecasts,
          fmt(results$rmse_benchmark, 3), fmt(results$rmse_augmented, 3),
          fmt(results$rmse_ratio, 3), fmt(results$dm_p_value, 3), results$verdict)
)
writeLines(c(
  "# Forecast evaluation",
  "",
  sprintf("Generated %s from %d country-months of mood index.", Sys.Date(), nrow(index)),
  "A ratio below 1 means adding the mood index lowered forecast errors.",
  "",
  table_lines
), "results/forecast_results.md")

cat(paste(table_lines, collapse = "\n"), "\n")
