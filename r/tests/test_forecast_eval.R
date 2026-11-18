# Run from the repository root:  Rscript r/tests/test_forecast_eval.R

library(testthat)
source("r/R/forecast_eval.R")

test_that("DM test finds no difference between identical forecasts", {
  set.seed(1)
  e <- rnorm(100)
  expect_true(is.na(dm_test(e, e)$p_value))
})

test_that("DM test detects a clearly better forecast", {
  set.seed(2)
  e_bench <- rnorm(200, sd = 2)
  e_aug   <- rnorm(200, sd = 1)
  result <- dm_test(e_bench, e_aug)
  expect_gt(result$statistic, 0)
  expect_lt(result$p_value, 0.01)
})

test_that("DM test treats a worse forecast as negative", {
  set.seed(3)
  result <- dm_test(rnorm(200, sd = 1), rnorm(200, sd = 2), horizon = 3)
  expect_lt(result$statistic, 0)
})

simulated_panel <- function(signal, n = 160, seed = 4) {
  set.seed(seed)
  mood <- as.numeric(arima.sim(list(ar = 0.7), n))
  past <- rnorm(n)
  data.frame(country = "ZZ", t = seq_len(n), past_change = past, mood = mood,
             target = 0.3 * past + signal * mood + rnorm(n, sd = 0.5))
}

test_that("the mood index helps when it truly predicts the target", {
  forecasts <- expanding_forecasts(simulated_panel(signal = 1), min_train = 40)
  summary <- summarise_forecasts(forecasts, "sim", "ZZ", horizon = 1)
  expect_lt(summary$rmse_ratio, 0.8)
  expect_lt(summary$dm_p_value, 0.01)
})

test_that("an irrelevant mood index does not look helpful", {
  forecasts <- expanding_forecasts(simulated_panel(signal = 0), min_train = 40)
  summary <- summarise_forecasts(forecasts, "sim", "ZZ", horizon = 1)
  expect_gt(summary$rmse_ratio, 0.97)
})

test_that("forecasts only use data available at the time", {
  panel <- simulated_panel(signal = 1, n = 60)
  horizon <- 3
  forecasts <- expanding_forecasts(panel, min_train = 20, horizon = horizon)
  # Poison the future: the first forecast must not change.
  first_t <- forecasts$t[1]
  poisoned <- panel
  poisoned$target[poisoned$t > first_t - horizon] <- 1e6
  poisoned$target[poisoned$t == first_t] <- panel$target[panel$t == first_t]
  again <- expanding_forecasts(poisoned, min_train = 20, horizon = horizon)
  expect_equal(again$augmented[1], forecasts$augmented[1])
})

test_that("rate panel builds future change and past change correctly", {
  rates <- data.frame(country = "US", month = sprintf("2020-%02d", 1:8),
                      rate = c(1, 1, 1, 2, 2, 2, 3, 3))
  index <- data.frame(country = "US", month = sprintf("2020-%02d", 1:8),
                      stance_index = c(0, 0, 0.3, 0.6, 0.9, 0.3, 0.3, 0.3))
  panel <- build_rate_panel(index, rates, horizon = 3, smooth = 3)
  expect_equal(panel$target[1], 1)       # Jan 1.0 -> Apr 2.0
  expect_equal(panel$past_change[4], 1)  # Jan 1.0 -> Apr 2.0
  expect_equal(panel$mood[5], 0.6)       # mean of Mar-May
  expect_true(is.na(panel$target[6]))    # no data 3 months after Jun
})

cat("All forecast evaluation tests passed.\n")
