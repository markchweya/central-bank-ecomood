# Fetch macro data from official SDMX REST APIs.
#
#   Policy rates: BIS, dataflow WS_CBPOL (monthly, end of period)
#   GDP growth:   OECD quarterly national accounts, real GDP,
#                 quarter-on-quarter growth in percent (seasonally adjusted)
#
# Results are cached as CSV under data/macro/ so repeated runs work offline.

# Country codes used in this project (ISO 3166 alpha-2, EA = euro area)
# mapped to the codes each source uses. NA means the source has no series.
COUNTRY_CODES <- data.frame(
  country = c("US", "EA", "GB", "JP", "CA", "IN", "KE"),
  bis     = c("US", "XM", "GB", "JP", "CA", "IN", NA),
  oecd    = c("USA", "EA", "GBR", "JPN", "CAN", "IND", NA),
  stringsAsFactors = FALSE
)

BIS_URL  <- "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.%s?format=csv&startPeriod=%s"
OECD_URL <- paste0(
  "https://sdmx.oecd.org/public/rest/data/",
  "OECD.SDD.NAD,DSD_NAMAIN1@DF_QNA_EXPENDITURE_GROWTH_OECD,/",
  "Q..%s.S1..B1GQ......G1.?startPeriod=%s&format=csv"
)

codes_for <- function(countries, source) {
  rows <- COUNTRY_CODES[match(countries, COUNTRY_CODES$country), ]
  missing <- countries[is.na(rows[[source]])]
  if (length(missing) > 0) {
    message(sprintf("No %s series for: %s (skipped)", toupper(source),
                    paste(missing, collapse = ", ")))
  }
  rows[!is.na(rows[[source]]), c("country", source)]
}

read_cached <- function(path, fetch, refresh) {
  if (file.exists(path) && !refresh) {
    return(utils::read.csv(path, stringsAsFactors = FALSE))
  }
  data <- fetch()
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
  utils::write.csv(data, path, row.names = FALSE)
  data
}

# Monthly policy rates: columns country, month ("YYYY-MM"), rate.
fetch_policy_rates <- function(countries, start = "2000-01",
                               cache = "data/macro/policy_rates.csv",
                               refresh = FALSE) {
  read_cached(cache, refresh = refresh, fetch = function() {
    codes <- codes_for(countries, "bis")
    url <- sprintf(BIS_URL, paste(codes$bis, collapse = "+"), start)
    raw <- utils::read.csv(url, stringsAsFactors = FALSE)
    data.frame(
      country = codes$country[match(raw$REF_AREA, codes$bis)],
      month   = raw$TIME_PERIOD,
      rate    = as.numeric(raw$OBS_VALUE),
      stringsAsFactors = FALSE
    )
  })
}

# Quarterly real GDP growth: columns country, quarter ("YYYY-Qn"), gdp_growth.
fetch_gdp_growth <- function(countries, start = "2000-Q1",
                             cache = "data/macro/gdp_growth.csv",
                             refresh = FALSE) {
  read_cached(cache, refresh = refresh, fetch = function() {
    codes <- codes_for(countries, "oecd")
    url <- sprintf(OECD_URL, paste(codes$oecd, collapse = "+"), start)
    raw <- utils::read.csv(url, stringsAsFactors = FALSE)
    raw <- raw[raw$ADJUSTMENT == "Y", ]  # seasonally and calendar adjusted
    data.frame(
      country    = codes$country[match(raw$REF_AREA, codes$oecd)],
      quarter    = raw$TIME_PERIOD,
      gdp_growth = as.numeric(raw$OBS_VALUE),
      stringsAsFactors = FALSE
    )
  })
}
