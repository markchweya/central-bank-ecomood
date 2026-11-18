# Out-of-sample test: does the mood index improve macro forecasts?
#
# Two exercises, each comparing a benchmark with the same model plus the
# relevant mood index, re-estimated on an expanding window:
#
#   Policy rate (monthly):  change in the policy rate over the next h months.
#     benchmark: rate change over the past h months
#     augmented: + stance index (mean over the past 3 months)
#
#   GDP (quarterly):        real GDP growth next quarter.
#     benchmark: AR(1) in GDP growth
#     augmented: + outlook index (quarterly mean)
#
# Forecast accuracy is compared with RMSE ratios and the Diebold-Mariano test
# (Harvey, Leybourne and Newbold small-sample version).

month_to_index <- function(month) {
  year <- as.integer(substr(month, 1, 4))
  mon  <- as.integer(substr(month, 6, 7))
  year * 12L + mon - 1L
}

month_to_quarter <- function(month) {
  mon <- as.integer(substr(month, 6, 7))
  sprintf("%s-Q%d", substr(month, 1, 4), (mon - 1L) %/% 3L + 1L)
}

# Mean of the current and previous (k - 1) values, needing all k present.
rolling_mean <- function(x, k) {
  out <- rep(NA_real_, length(x))
  if (length(x) >= k) {
    for (i in k:length(x)) out[i] <- mean(x[(i - k + 1):i])
  }
  out
}

# One row per country-month with the target, benchmark regressor and index.
build_rate_panel <- function(index, rates, horizon = 3, smooth = 3) {
  panels <- lapply(split(rates, rates$country), function(r) {
    r <- r[order(r$month), ]
    r$t <- month_to_index(r$month)
    full <- data.frame(t = seq(min(r$t), max(r$t)))
    full <- merge(full, r[, c("t", "rate")], by = "t", all.x = TRUE)
    country <- r$country[1]

    idx <- index[index$country == country, ]
    idx$t <- month_to_index(idx$month)
    full <- merge(full, idx[, c("t", "stance_index")], by = "t", all.x = TRUE)

    n <- nrow(full)
    lead_rate <- c(full$rate[-(1:horizon)], rep(NA, horizon))
    lag_rate  <- c(rep(NA, horizon), full$rate[1:(n - horizon)])
    data.frame(
      country     = country,
      t           = full$t,
      target      = lead_rate - full$rate,
      past_change = full$rate - lag_rate,
      mood        = rolling_mean(full$stance_index, smooth)
    )
  })
  do.call(rbind, panels)
}

# One row per country-quarter: next-quarter GDP growth, current growth, outlook.
build_gdp_panel <- function(index, gdp) {
  index$quarter <- month_to_quarter(index$month)
  outlook <- stats::aggregate(outlook_index ~ country + quarter, data = index,
                              FUN = mean)
  panels <- lapply(split(gdp, gdp$country), function(g) {
    g <- g[order(g$quarter), ]
    g <- merge(g, outlook, by = c("country", "quarter"), all.x = TRUE)
    g <- g[order(g$quarter), ]
    data.frame(
      country     = g$country,
      t           = seq_len(nrow(g)),
      quarter     = g$quarter,
      target      = c(g$gdp_growth[-1], NA),
      past_change = g$gdp_growth,
      mood        = g$outlook_index
    )
  })
  do.call(rbind, panels)
}

# Expanding-window forecasts for one country's panel. Rows need the target,
# benchmark regressor and mood index; the first `min_train` usable rows are
# only used for estimation. Forecasts for row i use rows that ended at least
# `horizon` periods earlier, so no future information leaks in.
expanding_forecasts <- function(panel, min_train = 24, horizon = 1) {
  panel <- panel[stats::complete.cases(panel[, c("target", "past_change", "mood")]), ]
  panel <- panel[order(panel$t), ]
  n <- nrow(panel)
  if (n <= min_train) return(NULL)
  rows <- lapply((min_train + 1):n, function(i) {
    train <- panel[panel$t <= panel$t[i] - horizon, ]
    if (nrow(train) < min_train) return(NULL)
    bench <- stats::lm(target ~ past_change, data = train)
    aug   <- stats::lm(target ~ past_change + mood, data = train)
    data.frame(
      t         = panel$t[i],
      actual    = panel$target[i],
      benchmark = stats::predict(bench, panel[i, ]),
      augmented = stats::predict(aug, panel[i, ])
    )
  })
  do.call(rbind, rows)
}

# Diebold-Mariano test of equal squared-error loss, with the Harvey et al.
# (1997) correction. Positive statistic: the augmented model is more accurate.
dm_test <- function(e_benchmark, e_augmented, horizon = 1) {
  d <- e_benchmark^2 - e_augmented^2
  n <- length(d)
  d_bar <- mean(d)
  lags <- horizon - 1
  gamma <- sapply(0:lags, function(k) {
    sum((d[(k + 1):n] - d_bar) * (d[1:(n - k)] - d_bar)) / n
  })
  variance <- (gamma[1] + 2 * sum(gamma[-1])) / n
  if (!is.finite(variance) || variance <= 0) {
    return(list(statistic = NA_real_, p_value = NA_real_))
  }
  correction <- sqrt((n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n)
  statistic <- correction * d_bar / sqrt(variance)
  list(statistic = statistic,
       p_value = 2 * stats::pt(-abs(statistic), df = n - 1))
}

rmse <- function(e) sqrt(mean(e^2))

summarise_forecasts <- function(forecasts, exercise, country, horizon) {
  e_bench <- forecasts$actual - forecasts$benchmark
  e_aug   <- forecasts$actual - forecasts$augmented
  dm <- dm_test(e_bench, e_aug, horizon)
  data.frame(
    exercise       = exercise,
    country        = country,
    n_forecasts    = nrow(forecasts),
    rmse_benchmark = rmse(e_bench),
    rmse_augmented = rmse(e_aug),
    rmse_ratio     = rmse(e_aug) / rmse(e_bench),
    dm_statistic   = dm$statistic,
    dm_p_value     = dm$p_value
  )
}

# Run one exercise for every country with enough data.
evaluate_panel <- function(panel, exercise, min_train, horizon) {
  results <- lapply(split(panel, panel$country), function(p) {
    forecasts <- expanding_forecasts(p, min_train = min_train, horizon = horizon)
    if (is.null(forecasts) || nrow(forecasts) < 8) {
      message(sprintf("%s %s: not enough overlapping data (skipped)",
                      exercise, p$country[1]))
      return(NULL)
    }
    summarise_forecasts(forecasts, exercise, p$country[1], horizon)
  })
  do.call(rbind, results)
}
