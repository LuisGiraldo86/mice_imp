
################################################################################
########## Script for Planned-Missing Calibration Comparison ###################
########## WD-FAB-DE Palnned-Missing Calibration outcomes    ###################
########## Feng, Heijdra Suasnabar drafted                   ###################
########## Oct, 2026                                         ###################
########## Questions: contact Feng: you-shan.feng@med.uni-tuebingen.de #########
################################################################################

#set directory#

setwd("E:/")
pathname<-"E:/"
getwd()

#Overall Packages: download & install#
#req_packages <- c("tidyverse", "haven", "logr", "dplyr", "caret", "skimr", "openxlsx", "ggplot2", "writexl", "rmcorr", "visdat", "patchwork")
#install.packages(req_packages, dependencies=TRUE)

library(tidyverse)
library(dplyr)
library(haven)
library(logr)
library(caret)
library(skimr)
library(openxlsx)
library(ggplot2)
library(writexl)
library(rmcorr)
library(visdat)
library(patchwork)


####################################
######## 1. Theta Comparions #######
####################################

WDFAB_thetas<- read_stata("WDFAB_ExperimentalData_ThetasMerged.dta")
attach(WDFAB_thetas)
WDFAB_thetas<-data.frame(WDFAB_thetas)

###settnig up mse and rmse with 95% CIs###

bootstrap_error_metrics <- function(actual, pred, B = 1000, conf = 0.95, seed = NULL) {
  
  if (length(actual) != length(pred)) {
    stop("actual and pred must have the same length")
  }
  
  if (!is.null(seed)) set.seed(seed)
  
  # Remove missing pairs
  complete <- complete.cases(actual, pred)
  actual <- actual[complete]
  pred <- pred[complete]
  
  # Sample size
  n <- length(actual)
  
  # Errors
  errors <- actual - pred
  
  # Actual MSE and RMSE
  mse <- mean(errors^2)
  rmse <- sqrt(mse)
  
  # Bootstrap
  mse_boot <- numeric(B)
  rmse_boot <- numeric(B)
  
  for (i in seq_len(B)) {
    boot_errors <- sample(errors, size = n, replace = TRUE)
    
    mse_boot[i] <- mean(boot_errors^2)
    rmse_boot[i] <- sqrt(mse_boot[i])
  }
  
  # Confidence interval
  alpha <- 1 - conf
  
  data.frame(
    n = n,
    
    MSE = mse,
    MSE_SE = sd(mse_boot),
    MSE_lower_CI = quantile(mse_boot, alpha / 2),
    MSE_upper_CI = quantile(mse_boot, 1 - alpha / 2),
    
    RMSE = rmse,
    RMSE_SE = sd(rmse_boot),
    RMSE_lower_CI = quantile(rmse_boot, alpha / 2),
    RMSE_upper_CI = quantile(rmse_boot, 1 - alpha / 2)
  )
}

set.seed(05082026)

###Main comparisons###

pred_cols <- c("CI_fiml_EAP", "CI_MG_EAP", "CI_SL_EAP", "ci_birt_theta", "ci_bmi_theta",
               "SD_fiml_EAP", "SD_MG_EAP", "SD_SL_EAP", "sd_birt_theta", "sd_bmi_theta", 
               "BI_fiml_EAP", "BI_MG_EAP", "BI_SL_EAP", "bi_birt_theta", "bi_bmi_theta")

pred_nb_cols <- c("CI_fiml_nb_EAP", "CI_MG_nb_EAP", "CInb_SL_EAP", "ci_nb_birt_theta", "ci_nb_bmi_theta",
                  "SD_fiml_nb_EAP", "SD_MG_nb_EAP", "SDnb_SL_EAP", "sd_nb_birt_theta", "sd_nb_bmi_theta", 
                  "BI_fiml_nb_EAP", "BI_MG_nb_EAP", "BInb_SL_EAP", "bi_nb_birt_theta", "bi_nb_bmi_theta")


pred_cols_s <- c("CI_fiml_EAP", "CI_MG_EAP", "CI_SL_EAP", "ci_birt_theta", "ci_bmi_theta",
               "SD_fiml_EAP", "SD_MG_EAP", "SD_SL_EAP", "sd_birt_theta", "sd_bmi_theta", 
               "BI_fiml_EAP", "BI_MG_EAP", "BI_SL_EAP", "bi_birt_theta", "bi_bmi_theta")

pred_nb_cols_s <- c("CI_fiml_nb_EAP", "CI_MG_nb_EAP", "CInb_SL_EAP", "ci_nb_birt_theta", "ci_nb_bmi_theta",
                  "SD_fiml_nb_EAP", "SD_MG_nb_EAP", "SDnb_SL_EAP", "sd_nb_birt_theta", "sd_nb_bmi_theta", 
                  "BI_fiml_nb_EAP", "BI_MG_nb_EAP", "BInb_SL_EAP", "bi_nb_birt_theta", "bi_nb_bmi_theta")


theta_compare <- lapply(pred_cols, function(p) {
  bootstrap_error_metrics(
    actual = WDFAB_thetas$nonmiss_EAP,
    pred = WDFAB_thetas[[p]],
    B = 2000
  )
})

theta_nb_compare <- lapply(pred_nb_cols, function(p) {
  bootstrap_error_metrics(
    actual = WDFAB_thetas$nonmiss_nb_EAP,
    pred = WDFAB_thetas[[p]],
    B = 2000
  )
})

###
theta_birt_compare <- lapply(pred_cols, function(p) {
  bootstrap_error_metrics(
    actual = WDFAB_thetas$nonmiss_birt,
    pred = WDFAB_thetas[[p]],
    B = 2000
  )
})
 
theta_nb_birt_compare <- lapply(pred_nb_cols, function(p) {
  bootstrap_error_metrics(
    actual = WDFAB_thetas$nonmiss_nb_birt,
    pred = WDFAB_thetas[[p]],
    B = 2000
  )
})

theta_compare <- do.call(rbind, theta_compare)
theta_nb_compare <- do.call(rbind, theta_nb_compare)
theta_birt_compare <- do.call(rbind, theta_birt_compare)
theta_nb_birt_compare <- do.call(rbind, theta_nb_birt_compare)

rownames(theta_compare) <- pred_cols
rownames(theta_nb_compare) <- pred_nb_cols
rownames(theta_birt_compare) <- pred_cols
rownames(theta_nb_birt_compare) <- pred_nb_cols

theta_compare <- data.frame(
  Model = rownames(theta_compare),
  theta_compare,
  row.names = NULL
)
theta_nb_compare <- data.frame(
  Model = rownames(theta_nb_compare),
  theta_nb_compare,
  row.names = NULL
)

theta_birt_compare <- data.frame(
  Model = rownames(theta_birt_compare),
  theta_birt_compare,
  row.names = NULL
)
theta_nb_birt_compare <- data.frame(
  Model = rownames(theta_nb_birt_compare),
  theta_nb_birt_compare,
  row.names = NULL
)

theta_comp_sheets <- list(
  "theta_compare" = theta_compare,
  "theta_nb_compare" = theta_nb_compare,
  "theta_birt_compare"  = theta_birt_compare,
  "theta_nb_birt_compare"  = theta_nb_birt_compare
)

write.xlsx(theta_comp_sheets, file = "theta_comp.xlsx", overwrite = TRUE)

###stratified#####

as.factor(WDFAB_thetas$age3cat)
as.factor(WDFAB_thetas$sex)
as.factor(WDFAB_thetas$srh3cat)
as.factor(WDFAB_thetas$Z_GRUND_RENTE)
as.factor(WDFAB_thetas$quart_nonmiss)

age_compare <- lapply(pred_cols, function(p) {
    WDFAB_thetas %>%
    group_by(age3cat) %>%
    group_modify(~ bootstrap_error_metrics(
      actual = .x$nonmiss_EAP,
      pred = .x[[p]],
      B = 2000
    )) %>%
    mutate(model = p,
    stratifier = "age")
})

age_nb_compare <- lapply(pred_nb_cols, function(p) {
  WDFAB_thetas %>%
    group_by(age3cat) %>%
    group_modify(~ bootstrap_error_metrics(
      actual = .x$nonmiss_nb_EAP,
      pred = .x[[p]],
      B = 2000
    )) %>%
    mutate(model = p,
           stratifier = "age")
})

sex_compare <- lapply(pred_cols, function(p) {
  WDFAB_thetas %>%
    group_by(sex) %>%
    group_modify(~ bootstrap_error_metrics(
      actual = .x$nonmiss_EAP,
      pred = .x[[p]],
      B = 2000
    )) %>%
    mutate(model = p,
  stratifier = "sex")
})
sex_nb_compare <- lapply(pred_nb_cols, function(p) {
  WDFAB_thetas %>%
    group_by(sex) %>%
    group_modify(~ bootstrap_error_metrics(
      actual = .x$nonmiss_nb_EAP,
      pred = .x[[p]],
      B = 2000
    )) %>%
    mutate(model = p,
           stratifier = "sex")
})

srh_compare <- lapply(pred_cols, function(p) {
  WDFAB_thetas %>%
    group_by(srh3cat) %>%
    group_modify(~ bootstrap_error_metrics(
      actual = .x$nonmiss_EAP,
      pred = .x[[p]],
      B = 2000
    )) %>%
    mutate(model = p,
  stratifier = "srh")
})
srh_nb_compare <- lapply(pred_nb_cols, function(p) {
  WDFAB_thetas %>%
    group_by(srh3cat) %>%
    group_modify(~ bootstrap_error_metrics(
      actual = .x$nonmiss_nb_EAP,
      pred = .x[[p]],
      B = 2000
    )) %>%
    mutate(model = p,
           stratifier = "srh")
})

rente_compare <- lapply(pred_cols, function(p) {
  WDFAB_thetas %>%
    group_by(Z_GRUND_RENTE) %>%
    group_modify(~ bootstrap_error_metrics(
      actual = .x$nonmiss_EAP,
      pred = .x[[p]],
      B = 2000
    )) %>%
    mutate(model = p,
  stratifier = "rente")
})
rente_nb_compare <- lapply(pred_nb_cols, function(p) {
  WDFAB_thetas %>%
    group_by(Z_GRUND_RENTE) %>%
    group_modify(~ bootstrap_error_metrics(
      actual = .x$nonmiss_nb_EAP,
      pred = .x[[p]],
      B = 2000
    )) %>%
    mutate(model = p,
           stratifier = "rente")
})

quart_compare <- lapply(pred_cols, function(p) {
  WDFAB_thetas %>%
    filter(!is.na(quart_nonmiss)) %>%
    group_by(quart_nonmiss) %>%
    group_modify(~ bootstrap_error_metrics(
      actual = .x$nonmiss_EAP,
      pred = .x[[p]],
      B = 2000
    )) %>%
    mutate(model = p,
           stratifier = "quart")
})
quart_nb_compare <- lapply(pred_nb_cols, function(p) {
  WDFAB_thetas %>%
    filter(!is.na(quart_nonmiss)) %>%
    group_by(quart_nonmiss) %>%
    group_modify(~ bootstrap_error_metrics(
      actual = .x$nonmiss_nb_EAP,
      pred = .x[[p]],
      B = 2000
    )) %>%
    mutate(model = p,
           stratifier = "quart")
})


age_compare <- do.call(rbind, age_compare)
sex_compare <- do.call(rbind, sex_compare)
srh_compare <- do.call(rbind, srh_compare)
rente_compare <- do.call(rbind, rente_compare)
quart_compare <- do.call(rbind, quart_compare)

age_nb_compare <- do.call(rbind, age_nb_compare)
sex_nb_compare <- do.call(rbind, sex_nb_compare)
srh_nb_compare <- do.call(rbind, srh_nb_compare)
rente_nb_compare <- do.call(rbind, rente_nb_compare)
quart_nb_compare <- do.call(rbind, quart_nb_compare)

Stratified_theta_comp_sheets <- list(
  "age_compare" = age_compare,
  "sex_compare" = sex_compare,
  "srh_compare"  = srh_compare,
  "rente_compare"  = rente_compare,
  "quart_nonmiss" = quart_nonmiss,
  "age_nb_compare"  = age_nb_compare,
  "sex_nb_compare"  = sex_nb_compare,
  "srh_nb_compare"  = srh_nb_compare,
  "rente_nb_compare"  = rente_nb_compare,
  "quart_nb_compare" = quart_nb_compare 
)

write.xlsx(Stratified_theta_comp_sheets, file = "Stratified_theta_comp.xlsx", overwrite = TRUE)

#plotting violin#

method_labels <- c(
  "FIML",
  "MG-IRT",
  "SL",
  "B-IRT",
  "MI+B-IRT",
  
  "FIML",
  "MG-IRT",
  "SL",
  "B-IRT",
  "MI+B-IRT",
  
  "FIML",
  "MG-IRT",
  "SL",
  "B-IRT",
  "MI+B-IRT"
)

set_labels <- c(
  "Common Item",
  "Common Item",
  "Common Item",
  "Common Item",
  "Common Item",
  
  "Standard Design",
  "Standard Design",
  "Standard Design",
  "Standard Design",
  "Standard Design",
  
  "Block-Interlaced",
  "Block-Interlaced",
  "Block-Interlaced",
  "Block-Interlaced",
  "Block-Interlaced"
)

make_ref_data <- function(
    data,
    vars_ref,
    reference
) {
  
  data %>%
    
    select(
      age3cat, sex, srh3cat, Z_GRUND_RENTE, quart_nonmiss,
      all_of(reference),
      all_of(vars_ref)
    ) %>%
    
    pivot_longer(
      cols = all_of(vars_ref),
      names_to = "variable",
      values_to = "value"
    ) %>%
    
    mutate(
      difference = value - .data[[reference]]
    ) %>%
    
    select(
      age3cat, sex, srh3cat, Z_GRUND_RENTE, quart_nonmiss,
      variable,
      difference
    )
}

plot_difference <- function(
    difference_data,
    stratify,
    reference_label = "Reference"
) {
  
  difference_data <- difference_data %>%
    mutate(
      .stratify = factor(.data[[stratify]]),
      method_set = factor(
        method_set,
        levels = c(
          "Common Item",
          "Standard Design",
          "Block-Interlaced"
        )
      ),
      method = factor(
        method,
        levels = c(
          "MI+B-IRT",
          "B-IRT",
          "SL",
          "MG-IRT",
          "FIML"
        )
      )
    ) %>%
    
    # Remove observations with missing stratification
    filter(
      !is.na(.stratify),
      !is.na(method_set),
      !is.na(method),
      !is.na(difference)
    )
  
  ggplot(
    difference_data,
    aes(
      x = difference,
      y = method
    )
  ) +
    
    geom_violin(
      fill = "#4C78A8",
      alpha = 0.5,
      trim = FALSE,
      scale = "width"
    ) +
    
    geom_boxplot(
      width = 0.15,
      outlier.shape = NA,
      fill = "white"
    ) +
    
    #    Optional dark line at "0"
    #    geom_vline(
    #      xintercept = 0,
    #      colour = "black",
    #      linewidth = 1
    #    ) +
    
    facet_grid(
      method_set ~ .stratify,
      scales = "free_y",
      space = "free_y",
      switch = "y"
    ) +
    
    labs(
      x = paste0(
        "Difference from ",
        reference_label,
        " (0 = no difference)"
      ),
      y = NULL
    ) +
    
    theme_classic() +
    
    theme(
      strip.background = element_rect(
        fill = "grey95",
        colour = NA
      ),
      strip.placement = "outside",
      strip.text = element_text(
        face = "bold"
      ),
      panel.grid.major.x = element_line(
        colour = "grey90",
        linewidth = 0.3
      ),
      panel.grid.minor = element_blank(),
      axis.text.y = element_text(size = 9)
    )
}

###
diff_ref <- make_ref_data(
  data = WDFAB_thetas,
  vars_ref = pred_cols_s,
  reference = "nonmiss_EAP"
)

diff_ref_nb <- make_ref_data(
  data = WDFAB_thetas,
  vars_ref = pred_nb_cols_s,
  reference = "nonmiss_nb_EAP"
)

method_lookup <- setNames(
  method_labels,
  pred_cols_s
)

set_lookup <- setNames(
  set_labels,
  pred_cols_s
)

method_lookup_nb <- setNames(
  method_labels,
  pred_nb_cols_s
)

set_lookup_nb <- setNames(
  set_labels,
  pred_nb_cols_s
)

diff_ref <- diff_ref %>%
  mutate(
    method = unname(
      method_lookup[as.character(variable)]
    ),
    
    method_set = unname(
      set_lookup[as.character(variable)]
    )
  )

diff_ref_nb <- diff_ref_nb %>%
  mutate(
    method = unname(
      method_lookup_nb[as.character(variable)]
    ),
    
    method_set = unname(
      set_lookup_nb[as.character(variable)]
    )
  )

diff_ref <- diff_ref %>%
  mutate(
    age3cat = factor(
      age3cat,
      levels = c(1, 2, 3),
      labels = c(
        "<50",
        "50-60",
        ">60"
      )
    ),
    
    sex = factor(
      sex,
      levels = c(1, 2),
      labels = c(
        "Women",
        "Men"
      )
    ),
    
    srh3cat = factor(
      srh3cat,
      levels = c(1, 2, 3),
      labels = c(
        "Very good/good",
        "Somewhat good",
        "Bad"
      )
    ),
    
    Z_GRUND_RENTE = factor(
      Z_GRUND_RENTE,
      levels = c(1, 2, 3, 4),
      labels = c(
        "Musculoskeletal",
        "Psycho-Somatic",
        "Inner Organ",
        "Other"
      )
    ),
    
    quart_nonmiss = factor(
      quart_nonmiss,
      levels = c(1, 2, 3, 4),
      labels = c(
        "Lowest quartile (Q1)",
        "Second quartile (Q2)",
        "Third quartile (Q3)",
        "Highest quartile (Q4)"
      )
    )
  )

diff_ref_nb <- diff_ref_nb %>%
  mutate(
    age3cat = factor(
      age3cat,
      levels = c(1, 2, 3),
      labels = c(
        "<50",
        "50-60",
        ">60"
      )
    ),
    
    sex = factor(
      sex,
      levels = c(1, 2),
      labels = c(
        "Women",
        "Men"
      )
    ),
    
    srh3cat = factor(
      srh3cat,
      levels = c(1, 2, 3),
      labels = c(
        "Very good/good",
        "Somewhat good",
        "Bad"
      )
    ),
    
    Z_GRUND_RENTE = factor(
      Z_GRUND_RENTE,
      levels = c(1, 2, 3, 4),
      labels = c(
        "Musculoskeletal",
        "Psycho-Somatic",
        "Inner Organ",
        "Other"
      )
    ),
    
    quart_nonmiss = factor(
      quart_nonmiss,
      levels = c(1, 2, 3, 4),
      labels = c(
        "Lowest quartile (Q1)",
        "Second quartile (Q2)",
        "Third quartile (Q3)",
        "Highest quartile (Q4)"
      )
    )
  )


violin_diff_age<- plot_difference(
  difference_data = diff_ref,
  stratify = "age3cat",
  reference_label = "Full-Form Reference"
)

violin_diff_sex<- plot_difference(
  difference_data = diff_ref,
  stratify = "sex",
  reference_label = "Full-Form Reference"
)

violin_diff_srt<- plot_difference(
  difference_data = diff_ref,
  stratify = "srh3cat",
  reference_label = "Full-Form Reference"
)

violin_diff_reha<- plot_difference(
  difference_data = diff_ref,
  stratify = "Z_GRUND_RENTE",
  reference_label = "Full-Form Reference"
)

violin_diff_quart<- plot_difference(
  difference_data = diff_ref,
  stratify = "quart_nonmiss",
  reference_label = "Full-Form Reference"
)

violin_diff_age_nb<- plot_difference(
  difference_data = diff_ref_nb,
  stratify = "age3cat",
  reference_label = "Full-Form Reference"
)

violin_diff_sex_nb<- plot_difference(
  difference_data = diff_ref_nb,
  stratify = "sex",
  reference_label = "Full-Form Reference"
)

violin_diff_srt_nb<- plot_difference(
  difference_data = diff_ref_nb,
  stratify = "srh3cat",
  reference_label = "Full-Form Reference"
)

violin_diff_reha_nb<- plot_difference(
  difference_data = diff_ref_nb,
  stratify = "Z_GRUND_RENTE",
  reference_label = "Full-Form Reference"
)

violin_diff_quart_nb<- plot_difference(
  difference_data = diff_ref_nb,
  stratify = "quart_nonmiss",
  reference_label = "Full-Form Reference"
)

ggsave("violin_diff_age.pdf", plot = violin_diff_age, width = 8, height = 6, units = "in")
ggsave("violin_diff_age.png", plot = violin_diff_age, width = 8, height = 6, units = "in", dpi = 1000 )
ggsave("violin_diff_sex.pdf", plot = violin_diff_sex, width = 8, height = 6, units = "in")
ggsave("violin_diff_sex.png", plot = violin_diff_sex, width = 8, height = 6, units = "in", dpi = 1000 )
ggsave("violin_diff_srt.pdf", plot = violin_diff_srt, width = 8, height = 6, units = "in")
ggsave("violin_diff_srt.png", plot = violin_diff_srt, width = 8, height = 6, units = "in", dpi = 1000 )
ggsave("violin_diff_reha.pdf", plot = violin_diff_reha, width = 8, height = 6, units = "in")
ggsave("violin_diff_reha.png", plot = violin_diff_reha, width = 8, height = 6, units = "in", dpi = 1000 )
ggsave("violin_diff_quart.pdf", plot = violin_diff_quart, width = 8, height = 6, units = "in")
ggsave("violin_diff_quart.png", plot = violin_diff_quart, width = 8, height = 6, units = "in", dpi = 1000 )

ggsave("violin_diff_age_nb.pdf", plot = violin_diff_age_nb, width = 8, height = 6, units = "in")
ggsave("violin_diff_age_nb.png", plot = violin_diff_age_nb, width = 8, height = 6, units = "in", dpi = 1000 )
ggsave("violin_diff_sex_nb.pdf", plot = violin_diff_sex_nb, width = 8, height = 6, units = "in")
ggsave("violin_diff_sex_nb.png", plot = violin_diff_sex_nb, width = 8, height = 6, units = "in", dpi = 1000 )
ggsave("violin_diff_srt_nb.pdf", plot = violin_diff_srt_nb, width = 8, height = 6, units = "in")
ggsave("violin_diff_srt_nb.png", plot = violin_diff_srt_nb, width = 8, height = 6, units = "in", dpi = 1000 )
ggsave("violin_diff_reha_nb.pdf", plot = violin_diff_reha_nb, width = 8, height = 6, units = "in")
ggsave("violin_diff_reha_nb.png", plot = violin_diff_reha_nb, width = 8, height = 6, units = "in", dpi = 1000 )
ggsave("violin_diff_quart_nb.pdf", plot = violin_diff_quart_nb, width = 8, height = 6, units = "in")
ggsave("violin_diff_quart_nb.png", plot = violin_diff_quart_nb, width = 8, height = 6, units = "in", dpi = 1000 )

####Bland-Altman graphics###

reference <- WDFAB_thetas$nonmiss_EAP
reference_nb <- WDFAB_thetas$nonmiss_nb_EAP

ci_pred_cols <- c("CI_fiml_EAP", "CI_MG_EAP", "CI_SL_EAP", "ci_birt_theta", "ci_bmi_theta")
sd_pred_cols <- c("SD_fiml_EAP", "SD_MG_EAP", "SD_SL_EAP", "sd_birt_theta", "sd_bmi_theta")
bi_pred_cols <- c("BI_fiml_EAP", "BI_MG_EAP", "BI_SL_EAP", "bi_birt_theta", "bi_bmi_theta")

ci_nb_pred_cols <- c("CI_fiml_nb_EAP", "CI_MG_nb_EAP", "CInb_SL_EAP", "ci_nb_birt_theta", "ci_nb_bmi_theta")
sd_nb_pred_cols <- c("SD_fiml_nb_EAP", "SD_MG_nb_EAP", "SDnb_SL_EAP", "sd_nb_birt_theta", "sd_nb_bmi_theta")
bi_nb_pred_cols <- c("BI_fiml_nb_EAP", "BI_MG_nb_EAP", "BInb_SL_EAP", "bi_nb_birt_theta", "bi_nb_bmi_theta")

ci_list <- lapply(ci_pred_cols, function(p) {
    diff <- WDFAB_thetas[[p]] - reference
  mean_value <- (WDFAB_thetas[[p]] + reference) / 2
  data.frame(
    method = p,
    mean = mean_value,
    difference = diff
  )
})
sd_list <- lapply(sd_pred_cols, function(p) {
  diff <- WDFAB_thetas[[p]] - reference
  mean_value <- (WDFAB_thetas[[p]] + reference) / 2
  data.frame(
    method = p,
    mean = mean_value,
    difference = diff
  )
})
bi_list <- lapply(bi_pred_cols, function(p) {
  diff <- WDFAB_thetas[[p]] - reference
  mean_value <- (WDFAB_thetas[[p]] + reference) / 2
  data.frame(
    method = p,
    mean = mean_value,
    difference = diff
  )
})

ci_nb_list <- lapply(ci_nb_pred_cols, function(p) {
  diff <- WDFAB_thetas[[p]] - reference_nb
  mean_value <- (WDFAB_thetas[[p]] + reference_nb) / 2
  data.frame(
    method = p,
    mean = mean_value,
    difference = diff
  )
})
sd_nb_list <- lapply(sd_nb_pred_cols, function(p) {
  diff <- WDFAB_thetas[[p]] - reference_nb
  mean_value <- (WDFAB_thetas[[p]] + reference_nb) / 2
  data.frame(
    method = p,
    mean = mean_value,
    difference = diff
  )
})
bi_nb_list <- lapply(bi_nb_pred_cols, function(p) {
  diff <- WDFAB_thetas[[p]] - reference_nb
  mean_value <- (WDFAB_thetas[[p]] + reference_nb) / 2
  data.frame(
    method = p,
    mean = mean_value,
    difference = diff
  )
})

ci_data <- do.call(rbind, ci_list)
sd_data <- do.call(rbind, sd_list)
bi_data <- do.call(rbind, bi_list)
ci_nb_data <- do.call(rbind, ci_nb_list)
sd_nb_data <- do.call(rbind, sd_nb_list)
bi_nb_data <- do.call(rbind, bi_nb_list)

###reference lines###
ci_ba_stats <- ci_data %>%
  group_by(method) %>%
  summarise(
    bias = mean(difference, na.rm = TRUE),
    sd = sd(difference, na.rm = TRUE),
    loa_upper = bias + 1.96 * sd,
    loa_lower = bias - 1.96 * sd,
    .groups = "drop"
  )

sd_ba_stats <- sd_data %>%
  group_by(method) %>%
  summarise(
    bias = mean(difference, na.rm = TRUE),
    sd = sd(difference, na.rm = TRUE),
    loa_upper = bias + 1.96 * sd,
    loa_lower = bias - 1.96 * sd,
    .groups = "drop"
  )

bi_ba_stats <- bi_data %>%
  group_by(method) %>%
  summarise(
    bias = mean(difference, na.rm = TRUE),
    sd = sd(difference, na.rm = TRUE),
    loa_upper = bias + 1.96 * sd,
    loa_lower = bias - 1.96 * sd,
    .groups = "drop"
  )

ci_nb_ba_stats <- ci_nb_data %>%
  group_by(method) %>%
  summarise(
    bias = mean(difference, na.rm = TRUE),
    sd = sd(difference, na.rm = TRUE),
    loa_upper = bias + 1.96 * sd,
    loa_lower = bias - 1.96 * sd,
    .groups = "drop"
  )

sd_nb_ba_stats <- sd_nb_data %>%
  group_by(method) %>%
  summarise(
    bias = mean(difference, na.rm = TRUE),
    sd = sd(difference, na.rm = TRUE),
    loa_upper = bias + 1.96 * sd,
    loa_lower = bias - 1.96 * sd,
    .groups = "drop"
  )

bi_nb_ba_stats <- bi_nb_data %>%
  group_by(method) %>%
  summarise(
    bias = mean(difference, na.rm = TRUE),
    sd = sd(difference, na.rm = TRUE),
    loa_upper = bias + 1.96 * sd,
    loa_lower = bias - 1.96 * sd,
    .groups = "drop"
  )

###plotting###

ci_method_labels <- c(
  "CI_fiml_EAP" = "FIML",
  "CI_MG_EAP" = "MG-IRT",
  "CI_SL_EAP" = "SL",
  "ci_birt_theta" = "B-IRT",
  "ci_bmi_theta" = "MI+B-IRT"
)

sd_method_labels <- c(
  "SD_fiml_EAP" = "FIML",
  "SD_MG_EAP" = "MG-IRT",
  "SD_SL_EAP" = "SL",
  "sd_birt_theta" = "B-IRT",
  "sd_bmi_theta" = "MI+B-IRT"
)

bi_method_labels <- c(
  "BI_fiml_EAP" = "FIML",
  "BI_MG_EAP" = "MG-IRT",
  "BI_SL_EAP" = "SL",
  "bi_birt_theta" = "B-IRT",
  "bi_bmi_theta" = "MI+B-IRT"
)

ci_plot <- ggplot(
  ci_data,
  aes(
    x = mean,
    y = difference,
    colour = method,
    shape = method
  )
) +
  geom_point(
    size = 2,
    alpha = 0.30
  ) +
  
  geom_hline(
    data = ci_ba_stats,
    aes(yintercept = bias, colour = method),
    linewidth = 0.8,
    inherit.aes = FALSE,
    show.legend = FALSE
  ) +
  
  geom_hline(
    data = ci_ba_stats,
    aes(yintercept = loa_upper, colour = method),
    linetype = "dashed",
    linewidth = 0.6,
    alpha = 0.5,
    inherit.aes = FALSE,
    show.legend = FALSE
  ) +
  
  geom_hline(
    data = ci_ba_stats,
    aes(yintercept = loa_lower, colour = method),
    linetype = "dashed",
    linewidth = 0.6,
    alpha = 0.5,
    inherit.aes = FALSE,
    show.legend = FALSE
  ) +
  
  scale_colour_manual(
    values = c(
      "CI_fiml_EAP" = "#009E73",
      "CI_MG_EAP"   = "#0072B2",
      "CI_SL_EAP"   = "#E69F00",
      "ci_birt_theta" = "#e7298a",
      "ci_bmi_theta" = "#BF3EFF"
    ),
    labels = method_labels,
    guide = guide_legend(nrow = 2, byrow = TRUE)
  ) +
  
  scale_shape_manual(
    values = c(
      "CI_fiml_EAP" = 16,
      "CI_MG_EAP" = 17,
      "CI_SL_EAP" = 15,
      "ci_birt_theta" = 21,
      "ci_bmi_theta" = 18
    ),
    labels = method_labels,
    guide = guide_legend(nrow = 2, byrow = TRUE)
  ) +
  
  labs(
    subtitle = "(a) Common Item",
    x = NULL,
    y = NULL,
    colour = "Calibration",
    shape = "Calibration"
  ) +
  
  theme_classic() +
  theme(
    legend.position = "bottom",
    legend.box = "horizontal",
    plot.title = element_text(
      hjust = 0.5,
      face = "bold",
      size = 14
    )
  )

sd_plot <- ggplot(
  sd_data,
  aes(
    x = mean,
    y = difference,
    colour = method,
    shape = method
  )
) +
  geom_point(
    size = 2,
    alpha = 0.30
  ) +
  
  geom_hline(
    data = sd_ba_stats,
    aes(yintercept = bias, colour = method),
    linewidth = 0.8,
    inherit.aes = FALSE,
    show.legend = FALSE
  ) +
  
  geom_hline(
    data = sd_ba_stats,
    aes(yintercept = loa_upper, colour = method),
    linetype = "dashed",
    linewidth = 0.6,
    alpha = 0.5,
    inherit.aes = FALSE,
    show.legend = FALSE
  ) +
  
  geom_hline(
    data = sd_ba_stats,
    aes(yintercept = loa_lower, colour = method),
    linetype = "dashed",
    linewidth = 0.6,
    alpha = 0.5,
    inherit.aes = FALSE,
    show.legend = FALSE
  ) +
  
  scale_colour_manual(
    values = c(
      "SD_fiml_EAP" = "#009E73",
      "SD_MG_EAP"   = "#0072B2",
      "SD_SL_EAP"   = "#E69F00",
      "sd_birt_theta" = "#e7298a",
      "sd_bmi_theta" = "#BF3EFF"
    ),
    labels = sd_method_labels,
    guide = guide_legend(nrow = 2, byrow = TRUE)
  ) + 
  
  scale_shape_manual(
    values = c(
      "SD_fiml_EAP" = 16,
      "SD_MG_EAP" = 17,
      "SD_SL_EAP" = 15,
      "sd_birt_theta" = 21,
      "sd_bmi_theta" = 18
    ),
    labels = sd_method_labels,
    guide = guide_legend(nrow = 2, byrow = TRUE)
  ) +
  
  labs(
    subtitle = "(b) Standard Design",
    x = NULL,
    y = "Difference in person-score estimates (planned-missing minus full-form)",
    colour = "Calibration",
    shape = "Calibration"
  ) +
  
  theme_classic() +
  theme(
    legend.position = "bottom",
    legend.box = "horizontal",
    plot.title = element_text(
      hjust = 0.5,
      face = "bold",
      size = 14
    )
  )

bi_plot <- ggplot(
  bi_data,
  aes(
    x = mean,
    y = difference,
    colour = method,
    shape = method
  )
) +
  geom_point(
    size = 2,
    alpha = 0.30
  ) +
  
  geom_hline(
    data = bi_ba_stats,
    aes(yintercept = bias, colour = method),
    linewidth = 0.8,
    inherit.aes = FALSE,
    show.legend = FALSE
  ) +
  
  geom_hline(
    data = bi_ba_stats,
    aes(yintercept = loa_upper, colour = method),
    linetype = "dashed",
    linewidth = 0.6,
    alpha = 0.5,
    inherit.aes = FALSE,
    show.legend = FALSE
  ) +
  
  geom_hline(
    data = bi_ba_stats,
    aes(yintercept = loa_lower, colour = method),
    linetype = "dashed",
    linewidth = 0.6,
    alpha = 0.5,
    inherit.aes = FALSE,
    show.legend = FALSE
  ) +
  
  scale_colour_manual(
    values = c(
      "BI_fiml_EAP" = "#009E73",
      "BI_MG_EAP"   = "#0072B2",
      "BI_SL_EAP"   = "#E69F00",
      "bi_birt_theta" = "#e7298a",
      "bi_bmi_theta" = "#BF3EFF"
    ),
    labels = bi_method_labels,
    guide = guide_legend(nrow = 2, byrow = TRUE)
  ) + 
  
  scale_shape_manual(
    values = c(
      "BI_fiml_EAP" = 16, #circle
      "BI_MG_EAP" = 17,   #triangle
      "BI_SL_EAP" = 15,   #square
      "bi_birt_theta" = 21, #inverted triangle
      "bi_bmi_theta" = 18      #diamond
    ),
    labels = bi_method_labels,
    guide = guide_legend(nrow = 2, byrow = TRUE)
  ) +
  
  labs(
    subtitle = "(c) Block-Interlaced",
    x = "Mean of full-form and planned-missing person-score estimates",
    y = NULL,
    colour = "Calibration",
    shape = "Calibration"
  ) +
  
  theme_classic() +
  theme(
    legend.position = "bottom",
    legend.box = "horizontal",
    plot.title = element_text(
      hjust = 0.5,
      face = "bold",
      size = 14
    )
  )

#exportin#
ggsave("CI_BlandAltman.pdf", plot = ci_plot, width = 8, height = 6, units = "in")
ggsave("CI_BlandAltman.png", plot = ci_plot, width = 8, height = 6, units = "in", dpi = 800 )

ggsave("SD_BlandAltman.pdf", plot = sd_plot, width = 8, height = 6, units = "in")
ggsave("SD_BlandAltman.png", plot = sd_plot, width = 8, height = 6, units = "in", dpi = 800)

ggsave("BI_BlandAltman.pdf", plot = bi_plot, width = 8, height = 6, units = "in")
ggsave("BI_BlandAltman.png", plot = bi_plot, width = 8, height = 6, units = "in", dpi = 800)

####combine#####

combined_ba <- (
  ci_plot /
    sd_plot /
    bi_plot
) +
  plot_layout(
    guides = "collect"
  ) &
  theme(
    legend.position = "bottom",
    legend.box = "horizontal"
  )

ggsave("BlandAltman_plots.pdf", plot = combined_ba, width = 5.35, height = 10, units = "in")
ggsave("BlandAltman_plots.png", plot = combined_ba, width = 5.35, height = 10, units = "in", dpi = 1000)


############Scatter plots##############

plot_ci_wide <- WDFAB_thetas %>%
  select(id_work, nonmiss_EAP, CI_fiml_EAP, CI_MG_EAP, CI_SL_EAP, ci_birt_theta, ci_bmi_theta)
plot_sd_wide <- WDFAB_thetas %>%
  select(id_work, nonmiss_EAP, SD_fiml_EAP, SD_MG_EAP, SD_SL_EAP, sd_birt_theta, sd_bmi_theta)
plot_bi_wide <- WDFAB_thetas %>%
  select(id_work, nonmiss_EAP, BI_fiml_EAP, BI_MG_EAP, BI_SL_EAP, bi_birt_theta, bi_bmi_theta)

plot_ci_long <- plot_ci_wide %>%
  pivot_longer(
    cols = -c(id_work, nonmiss_EAP),
    names_to = "Variable",
    values_to = "Value"
  )
plot_sd_long <- plot_sd_wide %>%
  pivot_longer(
    cols = -c(id_work, nonmiss_EAP),
    names_to = "Variable",
    values_to = "Value"
  )
plot_bi_long <- plot_bi_wide %>%
  pivot_longer(
    cols = -c(id_work, nonmiss_EAP),
    names_to = "Variable",
    values_to = "Value"
  )


ci_scatter <- ggplot(plot_ci_long, aes(x = nonmiss_EAP,
      y = Value,
      color = Variable,
      shape = Variable)
    ) +
    geom_point(
      size = 2,
      alpha = 0.30
    ) +
  geom_smooth(method = "lm", se = FALSE) +
    
    scale_colour_manual(
      values = c(
        "CI_fiml_EAP" = "#009E73",
        "CI_MG_EAP"   = "#0072B2",
        "CI_SL_EAP"   = "#E69F00",
        "ci_birt_theta" = "#e7298a",
        "ci_bmi_theta" = "#BF3EFF"
      ),
      labels = method_labels,
      guide = guide_legend(nrow = 2, byrow = TRUE)
    ) + 
    
    scale_shape_manual(
      values = c(
        "CI_fiml_EAP" = 16,
        "CI_MG_EAP" = 17,
        "CI_SL_EAP" = 15,
        "ci_birt_theta" = 21,
        "ci_bmi_theta" = 18
      ),
      labels = method_labels,
      guide = guide_legend(nrow = 2, byrow = TRUE)
    ) +
    
    labs(
      subtitle = "(a) Common Item",
      x = NULL,
      y = NULL,
      colour = "Calibration",
      shape = "Calibration"
    ) +
    
    theme_classic() +
    theme(
      legend.position = "bottom",
      legend.box = "horizontal",
      plot.title = element_text(
        hjust = 0.5,
        face = "bold",
        size = 14
      )
    )  


sd_scatter <- ggplot(plot_sd_long, aes(x = nonmiss_EAP,
  y = Value,
  color = Variable,
  shape = Variable)
) +
  geom_point(
    size = 2,
    alpha = 0.30
  ) +
  geom_smooth(method = "lm", se = FALSE) +
  
  scale_colour_manual(
    values = c(
      "SD_fiml_EAP" = "#009E73",
      "SD_MG_EAP"   = "#0072B2",
      "SD_SL_EAP"   = "#E69F00",
      "sd_birt_theta" = "#e7298a",
      "sd_bmi_theta" = "#BF3EFF"
    ),
    labels = method_labels,
    guide = guide_legend(nrow = 2, byrow = TRUE)
  ) +
  
  scale_shape_manual(
    values = c(
      "SD_fiml_EAP" = 16,
      "SD_MG_EAP" = 17,
      "SD_SL_EAP" = 15,
      "sd_birt_theta" = 21,
      "sd_bmi_theta" = 18
    ),
    labels = method_labels,
    guide = guide_legend(nrow = 2, byrow = TRUE)
  ) +
  
  labs(
    subtitle = "(b) Standard Design",
    x = NULL,
    y = "Person-score estimates: planned-missing",
    colour = "Calibration",
    shape = "Calibration"
  ) +
  
  theme_classic() +
  theme(
    legend.position = "bottom",
    legend.box = "horizontal",
    plot.title = element_text(
      hjust = 0.5,
      face = "bold",
      size = 14
    )
  )  


bi_scatter <- ggplot(plot_bi_long, aes(x = nonmiss_EAP,
                                       y = Value,
                                       color = Variable,
                                       shape = Variable)
) +
  geom_point(
    size = 2,
    alpha = 0.30
  ) +
  geom_smooth(method = "lm", se = FALSE) +
  
  scale_colour_manual(
    values = c(
      "BI_fiml_EAP" = "#009E73",
      "BI_MG_EAP"   = "#0072B2",
      "BI_SL_EAP"   = "#E69F00",
      "bi_birt_theta" = "#e7298a",
      "bi_bmi_theta" = "#BF3EFF"
    ),
    labels = method_labels,
    guide = guide_legend(nrow = 2, byrow = TRUE)
  ) +
  
  scale_shape_manual(
    values = c(
      "BI_fiml_EAP" = 16,
      "BI_MG_EAP" = 17,
      "BI_SL_EAP" = 15,
      "bi_birt_theta" = 21,
      "bi_bmi_theta" = 18
    ),
    labels = method_labels,
    guide = guide_legend(nrow = 2, byrow = TRUE)
  ) +
  
  labs(
    subtitle = "(c) Block-Interlaced",
    x = "Person-score estimates: full-form",
    y = NULL,
    colour = "Calibration",
    shape = "Calibration"
  ) +
  
  theme_classic() +
  theme(
    legend.position = "bottom",
    legend.box = "horizontal",
    plot.title = element_text(
      hjust = 0.5,
      face = "bold",
      size = 14
    )
  )  

#exportin#
ggsave("CI_scatter_theta.pdf", plot = ci_scatter, width = 8, height = 6, units = "in")
ggsave("CI_scatter_theta.png", plot = ci_scatter, width = 8, height = 6, units = "in", dpi = 600 )

ggsave("SD_scatter_theta.pdf", plot = sd_scatter, width = 8, height = 6, units = "in")
ggsave("SD_scatter_theta.png", plot = sd_scatter, width = 8, height = 6, units = "in", dpi = 600)

ggsave("BI_scatter_theta.pdf", plot = bi_scatter, width = 8, height = 6, units = "in")
ggsave("BI_scatter_theta.png", plot = bi_scatter, width = 8, height = 6, units = "in", dpi = 600)


###combining###

combined_scatter <- (
  ci_scatter /
    sd_scatter /
    bi_scatter
) +
  plot_layout(
    guides = "collect"
  ) &
  theme(
    legend.position = "bottom",
    legend.box = "horizontal") 

ggsave("scatter_theta.pdf", plot = combined_scatter, width = 5.35, height = 10, units = "in")
ggsave("scatter_theta.png", plot = combined_scatter, width = 5.35, height = 10, units = "in", dpi = 1000)


###########################################################
############ 2. Slope Parameter Comparsions ###############
###########################################################

###read in the extracted parameters data###

WDFAB_param_wide<- read_stata("ItemParameters_Wide.dta")
attach(WDFAB_param_wide)
WDFAB_param_wide<-data.frame(WDFAB_param_wide)

######Regressions Slope parameters ################################

miss_data_vars<- c("ci_fiml_a", "ci_mg_a", "ci_sl_a", "ci_birt_a", "ci_bmi_a", 
                   "sd_fiml_a", "sd_mg_a", "sd_sl_a", "sd_birt_a", "sd_bmi_a", 
                   "bi_fiml_a", "bi_mg_a", "bi_sl_a", "bi_birt_a", "bi_bmi_a")

miss_data_vars_nb<- c("ci_fiml_nb_a", "ci_mg_nb_a", "ci_sl_nb_a", "ci_nb_birt_a", "ci_nb_bmi_a",
                      "sd_fiml_nb_a", "sd_mg_nb_a", "sd_sl_nb_a", "sd_nb_birt_a", "sd_nb_bmi_a",
                      "bi_fiml_nb_a", "bi_mg_nb_a", "bi_sl_nb_a", "bi_nb_birt_a", "bi_nb_bmi_a")

reg_slopes <- lapply(miss_data_vars, function(p) {
  
  formula <- as.formula(
    paste("nonmiss_a ~", p)
  )
  
  model <- lm(formula, data = WDFAB_param_wide)
  
  summary_model <- summary(model)
  coef_model <- summary_model$coefficients
  
  data.frame(
    Predictor = p,
    B = coef_model[2, "Estimate"],
    SE = coef_model[2, "Std. Error"],
    CI_lower = coef_model[2, "Estimate"] -
      qt(0.975, df = df.residual(model)) * coef_model[2, "Std. Error"],
    CI_upper = coef_model[2, "Estimate"] +
      qt(0.975, df = df.residual(model)) * coef_model[2, "Std. Error"],
    t = coef_model[2, "t value"],
    p = coef_model[2, "Pr(>|t|)"],
    R2 = summary_model$r.squared,
    Adj_R2 = summary_model$adj.r.squared
  )
})

reg_slopes_nb <- lapply(miss_data_vars_nb, function(p) {
  
  formula <- as.formula(
    paste("nonmiss_nb_a ~", p)
  )
  
  model <- lm(formula, data = WDFAB_param_wide)
  
  summary_model <- summary(model)
  coef_model <- summary_model$coefficients
  
  data.frame(
    Predictor = p,
    B = coef_model[2, "Estimate"],
    SE = coef_model[2, "Std. Error"],
    CI_lower = coef_model[2, "Estimate"] -
      qt(0.975, df = df.residual(model)) * coef_model[2, "Std. Error"],
    CI_upper = coef_model[2, "Estimate"] +
      qt(0.975, df = df.residual(model)) * coef_model[2, "Std. Error"],
    t = coef_model[2, "t value"],
    p = coef_model[2, "Pr(>|t|)"],
    R2 = summary_model$r.squared,
    Adj_R2 = summary_model$adj.r.squared
  )
})

reg_slopes_sen <- lapply(miss_data_vars, function(p) {
  
  formula <- as.formula(
    paste("birt_a ~", p)
  )
  
  model <- lm(formula, data = WDFAB_param_wide)
  
  summary_model <- summary(model)
  coef_model <- summary_model$coefficients
  
  data.frame(
    Predictor = p,
    B = coef_model[2, "Estimate"],
    SE = coef_model[2, "Std. Error"],
    CI_lower = coef_model[2, "Estimate"] -
      qt(0.975, df = df.residual(model)) * coef_model[2, "Std. Error"],
    CI_upper = coef_model[2, "Estimate"] +
      qt(0.975, df = df.residual(model)) * coef_model[2, "Std. Error"],
    t = coef_model[2, "t value"],
    p = coef_model[2, "Pr(>|t|)"],
    R2 = summary_model$r.squared,
    Adj_R2 = summary_model$adj.r.squared
  )
})

reg_slopes_nb_sen <- lapply(miss_data_vars_nb, function(p) {
  
  formula <- as.formula(
    paste("birt_nb_a ~", p)
  )
  
  model <- lm(formula, data = WDFAB_param_wide)
  
  summary_model <- summary(model)
  coef_model <- summary_model$coefficients
  
  data.frame(
    Predictor = p,
    B = coef_model[2, "Estimate"],
    SE = coef_model[2, "Std. Error"],
    CI_lower = coef_model[2, "Estimate"] -
      qt(0.975, df = df.residual(model)) * coef_model[2, "Std. Error"],
    CI_upper = coef_model[2, "Estimate"] +
      qt(0.975, df = df.residual(model)) * coef_model[2, "Std. Error"],
    t = coef_model[2, "t value"],
    p = coef_model[2, "Pr(>|t|)"],
    R2 = summary_model$r.squared,
    Adj_R2 = summary_model$adj.r.squared
  )
})

reg_slopes_combined <- do.call(rbind, reg_slopes) 
reg_slopes_nb_combined <- do.call(rbind, reg_slopes_nb)
reg_slopes_sen_combined <- do.call(rbind, reg_slopes_sen)
reg_slopes_nb_sen_combined <- do.call(rbind, reg_slopes_nb_sen)

reg_slope_sheets <- list(
  "reg_slopes_combined" = reg_slopes_combined,
  "reg_slopes_nb_combined" = reg_slopes_nb_combined,
  "reg_slopes_sen_combined"  = reg_slopes_sen_combined,
  "reg_slopes_nb_sen_combined"  = reg_slopes_nb_sen_combined
)

write.xlsx(reg_slope_sheets, file = "reg_slope.xlsx", overwrite = TRUE)

#######################################################################
###### 3. clustered correlations for threshold parameters##############
#######################################################################

###reading in long data###

WDFAB_param<- read_stata("ItemParameters_Long_id.dta")
attach(WDFAB_param)
WDFAB_param<-data.frame(WDFAB_param)

WDFAB_param$item_id<-as.factor(WDFAB_param$item_id)


#####
ci_fiml_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = ci_fiml_b,
  dataset = WDFAB_param
)
ci_mg_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = ci_mg_b,
  dataset = WDFAB_param
)
ci_sl_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = ci_sl_b,
  dataset = WDFAB_param
)
ci_birt_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = ci_birt_b,
  dataset = WDFAB_param
)
ci_bmi_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = ci_bmi_b,
  dataset = WDFAB_param
)

ci_fiml_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = ci_fiml_nb_b,
  dataset = WDFAB_param
)
ci_mg_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = ci_mg_nb_b,
  dataset = WDFAB_param
)
ci_sl_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = ci_sl_nb_b,
  dataset = WDFAB_param
)
ci_birt_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = ci_nb_birt_b,
  dataset = WDFAB_param
)
ci_bmi_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = ci_nb_bmi_b,
  dataset = WDFAB_param
)

#####
sd_fiml_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = sd_fiml_b,
  dataset = WDFAB_param
)
sd_mg_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = sd_mg_b,
  dataset = WDFAB_param
)
sd_sl_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = sd_sl_b,
  dataset = WDFAB_param
)
sd_birt_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = sd_birt_b,
  dataset = WDFAB_param
)
sd_bmi_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = sd_bmi_b,
  dataset = WDFAB_param
)

sd_fiml_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = sd_fiml_nb_b,
  dataset = WDFAB_param
)
sd_mg_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = sd_mg_nb_b,
  dataset = WDFAB_param
)
sd_sl_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = sd_sl_nb_b,
  dataset = WDFAB_param
)
sd_birt_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = sd_nb_birt_b,
  dataset = WDFAB_param
)
sd_bmi_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = sd_nb_bmi_b,
  dataset = WDFAB_param
)

#####
bi_fiml_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = bi_fiml_b,
  dataset = WDFAB_param
)
bi_mg_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = bi_mg_b,
  dataset = WDFAB_param
)
bi_sl_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = bi_sl_b,
  dataset = WDFAB_param
)
bi_birt_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_b,
  measure2 = bi_birt_b,
  dataset = WDFAB_param
)
bi_bmi_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = bi_bmi_b,
  dataset = WDFAB_param
)

bi_fiml_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = bi_fiml_nb_b,
  dataset = WDFAB_param
)
bi_mg_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = bi_mg_nb_b,
  dataset = WDFAB_param
)
bi_sl_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = bi_sl_nb_b,
  dataset = WDFAB_param
)
bi_birt_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = bi_nb_birt_b,
  dataset = WDFAB_param
)
bi_bmi_nb_rm <- rmcorr(
  participant = item_id,
  measure1 = nonmiss_nb_b,
  measure2 = bi_nb_bmi_b,
  dataset = WDFAB_param
)

######Compared to BIRT full#######

ci_birt_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_b,
  measure2 = ci_birt_b,
  dataset = WDFAB_param
)
ci_bmi_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_b,
  measure2 = ci_bmi_b,
  dataset = WDFAB_param
)
ci_birt_nb_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_nb_b,
  measure2 = ci_nb_birt_b,
  dataset = WDFAB_param
)
ci_bmi_nb_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_nb_b,
  measure2 = ci_nb_bmi_b,
  dataset = WDFAB_param
)

sd_birt_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_b,
  measure2 = sd_birt_b,
  dataset = WDFAB_param
)
sd_bmi_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_b,
  measure2 = sd_bmi_b,
  dataset = WDFAB_param
)
sd_birt_nb_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_nb_b,
  measure2 = sd_nb_birt_b,
  dataset = WDFAB_param
)
sd_bmi_nb_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_nb_b,
  measure2 = sd_nb_bmi_b,
  dataset = WDFAB_param
)

bi_birt_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_b,
  measure2 = bi_birt_b,
  dataset = WDFAB_param
)
bi_bmi_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_b,
  measure2 = bi_bmi_b,
  dataset = WDFAB_param
)
bi_birt_nb_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_nb_b,
  measure2 = bi_nb_birt_b,
  dataset = WDFAB_param
)
bi_bmi_nb_rm_sen <- rmcorr(
  participant = item_id,
  measure1 = birt_nb_b,
  measure2 = bi_nb_bmi_b,
  dataset = WDFAB_param
)

#####

png(
  "CI_b_corr_small.png",
  width = 8,
  height = 14,
  units = "in",
  res = 600
)
ci_corr_plot_<-
  par(
  mfrow = c(6, 2),
  mar = c(4, 4, 3, 1),   # bottom, left, top, right
  oma = c(0, 0, 4, 0)
)
plot(ci_fiml_rm, main = "FIML")
plot(ci_fiml_nb_rm, main = "FIML  (no bike)")
plot(ci_mg_rm, main = "MB")
plot(ci_mg_nb_rm, main = "MB (no bike)")
plot(ci_sl_rm, main = "SL")
plot(ci_sl_nb_rm, main = "SL (no bike)")
plot(ci_birt_rm, main = "B-IRT")
plot(ci_birt_nb_rm, main = "B-IRT (no bike)")
plot(ci_bmi_rm, main = "MI+B-IRT")
plot(ci_bmi_nb_rm, main = "MI+B-IRT (no bike)")
mtext(
  "Common Item Treshold Correlations",
  outer = TRUE,
  cex = 1.3,
  font = 2
)
dev.off()


###
png(
  "SD_b_corr_small.png",
  width = 8,
  height = 14,
  units = "in",
  res = 600
)
sd_corr_plot<-
  par(
    mfrow = c(6, 2),
    mar = c(4, 4, 3, 1),   # bottom, left, top, right
    oma = c(0, 0, 4, 0)
  )
plot(sd_fiml_rm, main = "FIML")
plot(sd_fiml_nb_rm, main = "FIML  (no bike)")
plot(sd_mg_rm, main = "MB")
plot(sd_mg_nb_rm, main = "MB (no bike)")
plot(sd_sl_rm, main = "SL")
plot(sd_sl_nb_rm, main = "SL (no bike)")
plot(sd_birt_rm, main = "B-IRT")
plot(sd_birt_nb_rm, main = "B-IRT (no bike)")
plot(sd_bmi_rm, main = "MI+B-IRT")
plot(sd_bmi_nb_rm, main = "MI+B-IRT (no bike)")
mtext(
  "Standard Design Treshold Correlations",
  outer = TRUE,
  cex = 1.3,
  font = 2
)

dev.off()
###
png(
  "BI_b_corr_small.png",
  width = 8,
  height = 14,
  units = "in",
  res = 600
)

bi_corr_plot<-
  par(
    mfrow = c(6, 2),
    mar = c(4, 4, 3, 1),   # bottom, left, top, right
    oma = c(0, 0, 4, 0)
  )

plot(bi_fiml_rm, main = "FIML")
plot(bi_fiml_nb_rm, main = "FIML  (no bike)")
plot(bi_mg_rm, main = "MB")
plot(bi_mg_nb_rm, main = "MB (no bike)")
plot(bi_sl_rm, main = "SL")
plot(bi_sl_nb_rm, main = "SL (no bike)")
plot(bi_birt_rm, main = "B-IRT")
plot(bi_birt_nb_rm, main = "B-IRT (no bike)")
plot(bi_bmi_rm, main = "MI+B-IRT")
plot(bi_bmi_nb_rm, main = "MI+B-IRT (no bike)")
mtext(
  "Block-Interlaced Treshold Correlations",
  outer = TRUE,
  cex = 1.3,
  font = 2
)
dev.off()


###########Correlations table#########

methods <- c("ci_fiml_rm", "ci_mg_rm", "ci_sl_rm", "ci_birt_rm", "ci_bmi_rm", 
             "ci_fiml_nb_rm", "ci_mg_nb_rm", "ci_sl_nb_rm", "ci_birt_nb_rm", "ci_bmi_nb_rm",
             "sd_fiml_rm", "sd_mg_rm", "sd_sl_rm", "sd_birt_rm", "sd_bmi_rm", 
             "sd_fiml_nb_rm", "sd_mg_nb_rm", "sd_sl_nb_rm", "sd_birt_nb_rm", "sd_bmi_nb_rm", 
             "bi_fiml_rm", "bi_mg_rm", "bi_sl_rm", "bi_birt_rm", "bi_bmi_rm", 
             "bi_fiml_nb_rm", "bi_mg_nb_rm", "bi_sl_nb_rm", "bi_birt_nb_rm", "bi_bmi_nb_rm", 
             "ci_birt_rm_sen", "ci_bmi_rm_sen", 
             "ci_birt_nb_rm_sen", "ci_bmi_nb_rm_sen", 
             "sd_birt_rm_sen", "sd_bmi_rm_sen",   
             "sd_birt_nb_rm_sen", "sd_bmi_nb_rm_sen", 
             "bi_birt_rm_sen", "bi_bmi_rm_sen",  
             "bi_birt_nb_rm_sen", "bi_bmi_nb_rm_sen")

corr_results_table <- do.call(
  rbind,
  lapply(methods, function(x) {
    obj <- get(x)
    
    data.frame(
      Method = x,
      rho = obj$r,
      CI_lower = obj$CI[1],
      CI_upper = obj$CI[2],
      p_value = obj$p
    )
  })
)

rownames(corr_results_table) <- NULL
View(corr_results_table)

write_xlsx(
  corr_results_table,
  "beta_correlations.xlsx"
)

