

###########################################################################
########## Script for Planned-Missing calibration #########################
########## WD-FAB-DE Calibration Data             #########################
########## Feng, Heijdra Suasnabar drafted        #########################
########## Oct, 2026                              #########################
########## Questions: contact Feng: you-shan.feng@med.uni-tuebingen.de ####
###########################################################################

#set directory#

setwd("E:/")
pathname<-"E:/"
getwd()

#req_packages <- c("tidyverse", "mirt", "logr", "dplyr", "haven", "ggmirt", "openxlsx", "RcppParallel", "rstan")
#install.packages(req_packages, dependencies=TRUE)

library(tidyverse)
library(mirt)
library(logr)
library(dplyr)
library(haven)
library(ggmirt)
library(openxlsx)
library(RcppParallel)
library(rstan)

#Fetch & Set Up data#
WDFAB<- read_stata("WDFAB_ExperimentalData_FullAnchor_Jul2026_small.dta")
attach(WDFAB)
WDFAB<-data.frame(WDFAB)


#################################################################
#####Part 1: Full-form Community Mobility Analysis###############
#################################################################
WD_CM_id<-WDFAB[, c("DA051","DA053", "DA054", "DA055", "DA058", "DA060", "DA061", "DA062_r", "DA063_r", "DA064", "DA066", "DA067",
                      "DA052","DA068", "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074",
                      "Bike_1", "Bike_2_r_cor", "Bike_3", "Bike_4", "Bike_5", "Bike_6", "Bike_7", "id_work")]
WD_CM_nobike_id<-WDFAB[, c("DA051","DA053", "DA054", "DA055", "DA058", "DA060", "DA061", "DA062_r", "DA063_r", "DA064", "DA066", "DA067",
                    "DA052","DA068", "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074", "id_work")]


WD_CM_full<-WDFAB[, c("DA051","DA053", "DA054", "DA055", "DA058", "DA060", "DA061", "DA062_r", "DA063_r", "DA064", "DA066", "DA067",
                      "DA052","DA068", "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074",
                      "Bike_1", "Bike_2_r_cor", "Bike_3", "Bike_4", "Bike_5", "Bike_6", "Bike_7")]
WD_CM_nobike<-WDFAB[, c("DA051","DA053", "DA054", "DA055", "DA058", "DA060", "DA061", "DA062_r", "DA063_r", "DA064", "DA066", "DA067",
                      "DA052","DA068", "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074")]
WD_CM_drive<-WDFAB[, c("DA051","DA053", "DA054", "DA055", "DA058", "DA060", "DA061", "DA062_r", "DA063_r", "DA064", "DA066", "DA067")]
WD_CM_ride<-WDFAB[, c("DA052","DA068", "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074")]
WD_CM_bike<-WDFAB[, c("Bike_1", "Bike_2_r_cor", "Bike_3", "Bike_4", "Bike_5", "Bike_6", "Bike_7")]

CM_a<-na.omit(WD_CM_full)
CMD_a<-na.omit(WD_CM_drive)
CMR_a<-na.omit(WD_CM_ride)
CMB_a<-na.omit(WD_CM_bike)
CM_a_nobike<-na.omit(WD_CM_nobike)


#################################################
#######Part 1b: Anchor Subscales#################
#################################################

fit_CM_full<-mirt(WD_CM_full, 1, itemtype = "graded")
fit_CM_nb<-mirt(WD_CM_nobike, 1, itemtype = "graded")

par_CM_full<-coef(fit_CM_full, IRTpars = TRUE, simplify = TRUE)
par_CM_nb<-coef(fit_CM_nb, IRTpars = TRUE, simplify = TRUE)

round(par_CM_full$items, 3) # g = c = guessing parameter
round(par_CM_nb$items, 3) # g = c = guessing parameter

mfit_CM_f<-M2(fit_CM_full, type = "C2", calcNULL = FALSE)
mfit_CM_nb<-M2(fit_CM_nb, type = "C2", calcNULL = FALSE)

itemfit_CM_f_inout<-itemfit(fit_CM_full, fit_stats = "infit", p.adjust='fdr')
itemfit_CM_nb_inout<-itemfit(fit_CM_nb, fit_stats = "infit", p.adjust='fdr')

print(mfit_CM_f)
print(mfit_CM_nb)

print(itemfit_CM_f_inout)
print(itemfit_CM_nb_inout)

inout_CM_f<-itemfitPlot(fit_CM_full, fit_stats = "infit")
inout_CM_nb<-itemfitPlot(fit_CM_nb, fit_stats = "infit")

#png("PersonItemMap_CM_full.png", width = 1000, height = 2000)
RMX::plotPIccc(fit_CM_full)
#dev.off()

#png("InfitOutfit_CM_full.png", width = 700, height = 1000)
itemfitPlot(fit_CM_full, fit_stats = "infit", title = "Item Infit & Outfit Community Mobility")
#dev.off()


###ability scores###

theta_ml_CM_f <- fscores(fit_CM_full, method = 'ML')
theta_eap_CM_f <- fscores(fit_CM_full, method = 'EAP')

theta_ml_CM_mb <- fscores(fit_CM_nb, method = 'ML')
theta_eap_CM_mb <- fscores(fit_CM_nb, method = 'EAP')


###item reliability###

cm_theta_grid <- matrix(seq(-6, 6, length.out = 201), ncol = 1)
cm_nb_theta_grid <- matrix(seq(-6, 6, length.out = 201), ncol = 1)

cm_nitems <- extract.mirt(fit_CM_full, "nitems")
cm_nb_nitems <- extract.mirt(fit_CM_nb, "nitems")

cm_item_info <- matrix(NA, nrow = nrow(cm_theta_grid), ncol = cm_nitems)
cm_nb_item_info <- matrix(NA, nrow = nrow(cm_nb_theta_grid), ncol = cm_nb_nitems)

for(i in 1:cm_nitems){
  cm_item_obj <- extract.item(fit_CM_full, i)
  cm_item_info[, i] <- iteminfo(cm_item_obj, Theta = cm_theta_grid)
}

for(i in 1:cm_nb_nitems){
  cm_nb_item_obj <- extract.item(fit_CM_nb, i)
  cm_nb_item_info[, i] <- iteminfo(cm_nb_item_obj, Theta = cm_nb_theta_grid)
}

cm_mean_item_info <- colMeans(cm_item_info)
cm_nb_mean_item_info <- colMeans(cm_nb_item_info)

cm_mean_item_info
cm_nb_mean_item_info

##Anchor items: DA066	DA058	DA054 DA060	DA064	DA067

######################MIssing Data Approaches############################


WD_SD<- read_stata("WDFAB_ExperimentalData_CMStandard_Jul2026.dta")
attach(WD_SD)
WD_SD<-data.frame(WD_SD)

WD_CI<- read_stata("WDFAB_ExperimentalData_CMCommonItem_Jul2026.dta")
attach(WD_CI)
WD_CI<-data.frame(WD_CI)

WD_BI<- read_stata("WDFAB_ExperimentalData_CMBinterlaced_Jul2026.dta")
attach(WD_BI)
WD_BI<-data.frame(WD_BI)

SD_CM_full_id<-WD_SD[, c("DA051","DA053", "DA054", "DA055", "DA058", "DA060", "DA061", "DA062_r", "DA063_r", "DA064", "DA066", "DA067",
                      "DA052","DA068", "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074",
                      "Bike_1", "Bike_2_r_cor", "Bike_3", "Bike_4", "Bike_5", "Bike_6", "Bike_7", "grp_final", "id_work")]
SD_CM_nobike_id<-WD_SD[, c("DA051","DA053", "DA054", "DA055", "DA058", "DA060", "DA061", "DA062_r", "DA063_r", "DA064", "DA066", "DA067",
                        "DA052","DA068", "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074", "grp_final", "id_work")]
CI_CM_full_id<-WD_CI[, c("DA051","DA053", "DA054", "DA055", "DA058", "DA060", "DA061", "DA062_r", "DA063_r", "DA064", "DA066", "DA067",
                      "DA052","DA068", "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074",
                      "Bike_1", "Bike_2_r_cor", "Bike_3", "Bike_4", "Bike_5", "Bike_6", "Bike_7", "grp_final", "id_work")]
CI_CM_nobike_id<-WD_CI[, c("DA051","DA053", "DA054", "DA055", "DA058", "DA060", "DA061", "DA062_r", "DA063_r", "DA064", "DA066", "DA067",
                        "DA052","DA068", "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074", "grp_final", "id_work")]
BI_CM_full_id<-WD_BI[, c("DA051","DA053", "DA054", "DA055", "DA058", "DA060", "DA061", "DA062_r", "DA063_r", "DA064", "DA066", "DA067",
                      "DA052","DA068", "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074",
                      "Bike_1", "Bike_2_r_cor", "Bike_3", "Bike_4", "Bike_5", "Bike_6", "Bike_7", "grp_final", "id_work")]
BI_CM_nobike_id<-WD_BI[, c("DA051","DA053", "DA054", "DA055", "DA058", "DA060", "DA061", "DA062_r", "DA063_r", "DA064", "DA066", "DA067",
                        "DA052","DA068", "DA069_r", "DA070", "DA071", "DA072", "DA073", "DA074", "grp_final", "id_work")]

CI_CM_full<-subset(CI_CM_full_id, select = -c(id_work, grp_final))
SD_CM_full<-subset(SD_CM_full_id, select = -c(id_work, grp_final))
BI_CM_full<-subset(BI_CM_full_id, select = -c(id_work, grp_final))
CI_CM_nobike<-subset(CI_CM_nobike_id, select = -c(id_work, grp_final))
SD_CM_nobike<-subset(SD_CM_nobike_id, select = -c(id_work, grp_final))
BI_CM_nobike<-subset(BI_CM_nobike_id, select = -c(id_work, grp_final))

#################################################
#######Part 2: FIML likelihood ##################
#################################################

fit_SD_full<-mirt(SD_CM_full, 1, itemtype = "graded")
fit_SD_nb<-mirt(SD_CM_nobike, 1, itemtype = "graded")
fit_CI_full<-mirt(CI_CM_full, 1, itemtype = "graded")
fit_CI_nb<-mirt(CI_CM_nobike, 1, itemtype = "graded")
fit_BI_full<-mirt(BI_CM_full, 1, itemtype = "graded")
fit_BI_nb<-mirt(BI_CM_nobike, 1, itemtype = "graded")

extract_pars <- function(model) {
  pars <- coef(model, IRTpars = TRUE, simplify = TRUE)$items
  
  # Convert matrix to data frame and move item names into a dedicated column
  as.data.frame(pars) %>% 
    tibble::rownames_to_column(var = "Item")
}

par_SD_full<-extract_pars(fit_SD_full)
par_SD_nb<-extract_pars(fit_SD_nb)
par_CI_full<-extract_pars(fit_CI_full)
par_CI_nb<-extract_pars(fit_CI_nb)
par_BI_full<-extract_pars(fit_BI_full)
par_BI_nb<-extract_pars(fit_BI_nb)

###export to excel###
fiml_par_sheets <- list(
  "CI_Full"  = par_CI_full,
  "CI_nobike"  = par_CI_nb,
  "SD_Full"  = par_SD_full,
  "SD_nobike"  = par_SD_nb,
  "BI_Full"  = par_BI_full,
  "BI_nobike"  = par_BI_nb
)

write.xlsx(fiml_par_sheets, file = "FIML_Item_Parameters.xlsx", overwrite = TRUE)

###########################################
########Part 3: Multi-group ###############
###########################################

CI_CM_full_id$grp_final <- factor(CI_CM_full_id$grp_final)
SD_CM_full_id$grp_final <- factor(SD_CM_full_id$grp_final)
BI_CM_full_id$grp_final <- factor(BI_CM_full_id$grp_final)

ci_anchor <- c("DA066", "DA058", "DA054", "DA060", "DA064", "DA067")
ci_group_var <- as.factor(CI_CM_full_id$grp_final)
sd_group_var <- as.factor(SD_CM_full_id$grp_final)
bi_group_var <- as.factor(BI_CM_full_id$grp_final)

ci_mg_fit <- multipleGroup(
  CI_CM_full, 1,
  group = ci_group_var,
  itemtype = "graded",
  invariance = c(ci_anchor, "free_means", "free_var")  # constrain anchor parameters equal
)
ci_mg_nb_fit <- multipleGroup(
  CI_CM_nobike, 1,
  group = ci_group_var,
  itemtype = "graded",
  invariance = c(ci_anchor, "free_means", "free_var")  # constrain anchor parameters equal
)

sd_mg_fit <- multipleGroup(
  SD_CM_full, 1,
  group = sd_group_var,
  itemtype = "graded",
  invariance = c(ci_anchor, "free_means", "free_var")  # constrain anchor parameters equal
)
sd_mg_nb_fit <- multipleGroup(
  SD_CM_nobike, 1,
  group = sd_group_var,
  itemtype = "graded",
  invariance = c(ci_anchor, "free_means", "free_var")  # constrain anchor parameters equal
)

bi_mg_fit <- multipleGroup(
  BI_CM_full, 1,
  group = bi_group_var,
  itemtype = "graded",
  invariance = c(ci_anchor, "free_means", "free_var")  # constrain anchor parameters equal
)
bi_mg_nb_fit <- multipleGroup(
  BI_CM_nobike, 1,
  group = bi_group_var,
  itemtype = "graded",
  invariance = c(ci_anchor, "free_means", "free_var")  # constrain anchor parameters equal
)

par_sd_mg<-coef(sd_mg_fit, IRTpars = TRUE, simplify = TRUE)
par_sd_nb_mg<-coef(sd_mg_nb_fit, IRTpars = TRUE, simplify = TRUE)
par_ci_mg<-coef(ci_mg_fit, IRTpars = TRUE, simplify = TRUE)
par_ci_nb_mg<-coef(ci_mg_nb_fit, IRTpars = TRUE, simplify = TRUE)
par_bi_mg<-coef(bi_mg_fit, IRTpars = TRUE, simplify = TRUE)
par_bi_nb_mg<-coef(bi_mg_nb_fit, IRTpars = TRUE, simplify = TRUE)

print(par_sd_mg)
print(par_sd_nb_mg)
print(par_ci_mg)
print(par_ci_nb_mg)
print(par_bi_mg)
print(par_bi_nb_mg)

###Model Parameters###

extract_mg_group_pars <- function(mg_coef_list, group_name) {
  # Extract the $items matrix for the specified group
  group_items <- mg_coef_list[[group_name]]$items
  
  # Convert to data frame and preserve item names
  as.data.frame(group_items) %>% 
    tibble::rownames_to_column(var = "Item")
}

par_ci_mg_A <- extract_mg_group_pars(par_ci_mg, 1) 
par_ci_mg_B <- extract_mg_group_pars(par_ci_mg, 2)
par_ci_mg_C <- extract_mg_group_pars(par_ci_mg, 3)
par_ci_nb_mg_A <- extract_mg_group_pars(par_ci_nb_mg, 1) 
par_ci_nb_mg_B <- extract_mg_group_pars(par_ci_nb_mg, 2)
par_ci_nb_mg_C <- extract_mg_group_pars(par_ci_nb_mg, 3)

par_sd_mg_A <- extract_mg_group_pars(par_sd_mg, 1) 
par_sd_mg_B <- extract_mg_group_pars(par_sd_mg, 2)
par_sd_mg_C <- extract_mg_group_pars(par_sd_mg, 3)
par_sd_nb_mg_A <- extract_mg_group_pars(par_sd_nb_mg, 1) 
par_sd_nb_mg_B <- extract_mg_group_pars(par_sd_nb_mg, 2)
par_sd_nb_mg_C <- extract_mg_group_pars(par_sd_nb_mg, 3)

par_bi_mg_A <- extract_mg_group_pars(par_bi_mg, 1) 
par_bi_mg_B <- extract_mg_group_pars(par_bi_mg, 2)
par_bi_mg_C <- extract_mg_group_pars(par_bi_mg, 3)
par_bi_nb_mg_A <- extract_mg_group_pars(par_bi_nb_mg, 1) 
par_bi_nb_mg_B <- extract_mg_group_pars(par_bi_nb_mg, 2)
par_bi_nb_mg_C <- extract_mg_group_pars(par_bi_nb_mg, 3)


mgirt_par_sheets <- list(
  "MG_CI_Full_A"  = par_ci_mg_A,
  "MG_CI_Full_B"  = par_ci_mg_B,
  "MG_CI_Full_C"  = par_ci_mg_C,
  "MG_CI_nobike_A"  = par_ci_nb_mg_A,
  "MG_CI_nobike_B"  = par_ci_nb_mg_B,
  "MG_CI_nobike_C"  = par_ci_nb_mg_C,
  "MG_SD_Full_A"  = par_sd_mg_A,
  "MG_SD_Full_B"  = par_sd_mg_B,
  "MG_SD_Full_C"  = par_sd_mg_C,
  "MG_SD_nobike_A"  = par_sd_nb_mg_A,
  "MG_SD_nobike_B"  = par_sd_nb_mg_B,
  "MG_SD_nobike_C"  = par_sd_nb_mg_C,
  "MG_BI_Full_A"  = par_bi_mg_A,
  "MG_BI_Full_B"  = par_bi_mg_B,
  "MG_BI_Full_C"  = par_bi_mg_C,
  "MG_BI_nobike_A"  = par_bi_nb_mg_A,
  "MG_BI_nobike_B"  = par_bi_nb_mg_B,
  "MG_BI_nobike_C"  = par_bi_nb_mg_C
)

write.xlsx(mgirt_par_sheets, file = "MGIRT_Item_Parameters.xlsx", overwrite = TRUE)

###########################################
########Part 4: Test Equating##############
###########################################

###4A — Separate Calibrations###
#install.packages("lordif")
library(plink)

#setting anchors#

#common item#
anchor_ci<-c("DA066",	"DA058",	"DA054",	"DA060",	"DA064",	"DA067")

#standrad-design#  
anchor_sd_ab<-c("DA066",	"DA060",	"DA064")
anchor_sd_ac<-c("DA058",	"DA054",	"DA067")

#Block-interlaced#
anchor_bi_ab<-c("DA058",	"DA064")
anchor_bi_bc<-c("DA054",	"DA067")
anchor_bi_ac<-c("DA066",	"DA060")

anchor_bi<-c("DA058",	"DA064", "DA066",	"DA060")

#setting subsets#

CI_CM_full_a_id<-subset(CI_CM_full_id, grp_final %in% c(1))
CI_CM_full_b_id<-subset(CI_CM_full_id, grp_final %in% c(2))
CI_CM_full_c_id<-subset(CI_CM_full_id, grp_final %in% c(3))

SD_CM_full_a_id<-subset(SD_CM_full_id, grp_final %in% c(1))
SD_CM_full_b_id<-subset(SD_CM_full_id, grp_final %in% c(2))
SD_CM_full_c_id<-subset(SD_CM_full_id, grp_final %in% c(3))

BI_CM_full_a_id<-subset(BI_CM_full_id, grp_final %in% c(1))
BI_CM_full_b_id<-subset(BI_CM_full_id, grp_final %in% c(2))
BI_CM_full_c_id<-subset(BI_CM_full_id, grp_final %in% c(3))

CI_CM_nb_a_id<-subset(CI_CM_nobike_id, grp_final %in% c(1))
CI_CM_nb_b_id<-subset(CI_CM_nobike_id, grp_final %in% c(2))
CI_CM_nb_c_id<-subset(CI_CM_nobike_id, grp_final %in% c(3))

SD_CM_nb_a_id<-subset(SD_CM_nobike_id, grp_final %in% c(1))
SD_CM_nb_b_id<-subset(SD_CM_nobike_id, grp_final %in% c(2))
SD_CM_nb_c_id<-subset(SD_CM_nobike_id, grp_final %in% c(3))

BI_CM_nb_a_id<-subset(BI_CM_nobike_id, grp_final %in% c(1))
BI_CM_nb_b_id<-subset(BI_CM_nobike_id, grp_final %in% c(2))
BI_CM_nb_c_id<-subset(BI_CM_nobike_id, grp_final %in% c(3))

CI_CM_full_a<-subset(CI_CM_full_a_id, select = -c(id_work, grp_final))
CI_CM_full_b<-subset(CI_CM_full_b_id, select = -c(id_work, grp_final))
CI_CM_full_c<-subset(CI_CM_full_c_id, select = -c(id_work, grp_final))

SD_CM_full_a<-subset(SD_CM_full_a_id, select = -c(id_work, grp_final))
SD_CM_full_b<-subset(SD_CM_full_b_id, select = -c(id_work, grp_final))
SD_CM_full_c<-subset(SD_CM_full_c_id, select = -c(id_work, grp_final))

BI_CM_full_a<-subset(BI_CM_full_a_id, select = -c(id_work, grp_final))
BI_CM_full_b<-subset(BI_CM_full_b_id, select = -c(id_work, grp_final))
BI_CM_full_c<-subset(BI_CM_full_c_id, select = -c(id_work, grp_final))

CI_CM_nb_a<-subset(CI_CM_nb_a_id, select = -c(id_work, grp_final))
CI_CM_nb_b<-subset(CI_CM_nb_b_id, select = -c(id_work, grp_final))
CI_CM_nb_c<-subset(CI_CM_nb_c_id, select = -c(id_work, grp_final))

SD_CM_nb_a<-subset(SD_CM_nb_a_id, select = -c(id_work, grp_final))
SD_CM_nb_b<-subset(SD_CM_nb_b_id, select = -c(id_work, grp_final))
SD_CM_nb_c<-subset(SD_CM_nb_c_id, select = -c(id_work, grp_final))

BI_CM_nb_a<-subset(BI_CM_nb_a_id, select = -c(id_work, grp_final))
BI_CM_nb_b<-subset(BI_CM_nb_b_id, select = -c(id_work, grp_final))
BI_CM_nb_c<-subset(BI_CM_nb_c_id, select = -c(id_work, grp_final))

CI_CM_full_a <- CI_CM_full_a %>%
  select_if(~ mean(is.na(.)) < 0.6)
CI_CM_full_b <- CI_CM_full_b %>%
  select_if(~ mean(is.na(.)) < 0.6)
CI_CM_full_c <- CI_CM_full_c %>%
  select_if(~ mean(is.na(.)) < 0.6)

CI_CM_nb_a <- CI_CM_nb_a %>%
  select_if(~ mean(is.na(.)) < 0.6)
CI_CM_nb_b <- CI_CM_nb_b %>%
  select_if(~ mean(is.na(.)) < 0.6)
CI_CM_nb_c <- CI_CM_nb_c %>%
  select_if(~ mean(is.na(.)) < 0.6)

SD_CM_full_a <- SD_CM_full_a %>%
  select_if(~ mean(is.na(.)) < 0.6)
SD_CM_full_b <- SD_CM_full_b %>%
  select_if(~ mean(is.na(.)) < 0.6)
SD_CM_full_c <- SD_CM_full_c %>%
  select_if(~ mean(is.na(.)) < 0.6)

SD_CM_nb_a <- SD_CM_nb_a %>%
  select_if(~ mean(is.na(.)) < 0.6)
SD_CM_nb_b <- SD_CM_nb_b %>%
  select_if(~ mean(is.na(.)) < 0.6)
SD_CM_nb_c <- SD_CM_nb_c %>%
  select_if(~ mean(is.na(.)) < 0.6)

BI_CM_full_a <- BI_CM_full_a %>%
  select_if(~ mean(is.na(.)) < 0.6)
BI_CM_full_b <- BI_CM_full_b %>%
  select_if(~ mean(is.na(.)) < 0.6)
BI_CM_full_c <- BI_CM_full_c %>%
  select_if(~ mean(is.na(.)) < 0.6)

BI_CM_nb_a <- BI_CM_nb_a %>%
  select_if(~ mean(is.na(.)) < 0.6)
BI_CM_nb_b <- BI_CM_nb_b %>%
  select_if(~ mean(is.na(.)) < 0.6)
BI_CM_nb_c <- BI_CM_nb_c %>%
  select_if(~ mean(is.na(.)) < 0.6)


#subset grm#

fit_SD_full_a<-mirt(SD_CM_full_a, 1, itemtype = "graded")
fit_SD_full_b<-mirt(SD_CM_full_b, 1, itemtype = "graded")
fit_SD_full_c<-mirt(SD_CM_full_c, 1, itemtype = "graded")

fit_SD_nb_a<-mirt(SD_CM_nb_a, 1, itemtype = "graded")
fit_SD_nb_b<-mirt(SD_CM_nb_b, 1, itemtype = "graded")
fit_SD_nb_c<-mirt(SD_CM_nb_c, 1, itemtype = "graded")

fit_CI_full_a<-mirt(CI_CM_full_a, 1, itemtype = "graded")
fit_CI_full_b<-mirt(CI_CM_full_b, 1, itemtype = "graded")
fit_CI_full_c<-mirt(CI_CM_full_c, 1, itemtype = "graded")

fit_CI_nb_a<-mirt(CI_CM_nb_a, 1, itemtype = "graded")
fit_CI_nb_b<-mirt(CI_CM_nb_b, 1, itemtype = "graded")
fit_CI_nb_c<-mirt(CI_CM_nb_c, 1, itemtype = "graded")

fit_BI_full_a<-mirt(BI_CM_full_a, 1, itemtype = "graded")
fit_BI_full_b<-mirt(BI_CM_full_b, 1, itemtype = "graded")
fit_BI_full_c<-mirt(BI_CM_full_c, 1, itemtype = "graded")

fit_BI_nb_a<-mirt(BI_CM_nb_a, 1, itemtype = "graded")
fit_BI_nb_b<-mirt(BI_CM_nb_b, 1, itemtype = "graded")
fit_BI_nb_c<-mirt(BI_CM_nb_c, 1, itemtype = "graded")

##########

ci_plink_A <- read.mirt(fit_CI_full_a, itemtype = "grad")
ci_plink_B <- read.mirt(fit_CI_full_b, itemtype = "grad")
ci_plink_C <- read.mirt(fit_CI_full_c, itemtype = "grad")

sd_plink_A <- read.mirt(fit_SD_full_a, itemtype = "grad")
sd_plink_B <- read.mirt(fit_SD_full_b, itemtype = "grad")
sd_plink_C <- read.mirt(fit_SD_full_c, itemtype = "grad")

bi_plink_A <- read.mirt(fit_BI_full_a, itemtype = "grad")
bi_plink_B <- read.mirt(fit_BI_full_b, itemtype = "grad")
bi_plink_C <- read.mirt(fit_BI_full_c, itemtype = "grad")

ci_plink_A_nb <- read.mirt(fit_CI_nb_a, itemtype = "grad")
ci_plink_B_nb <- read.mirt(fit_CI_nb_b, itemtype = "grad")
ci_plink_C_nb <- read.mirt(fit_CI_nb_c, itemtype = "grad")

sd_plink_A_nb <- read.mirt(fit_SD_nb_a, itemtype = "grad")
sd_plink_B_nb <- read.mirt(fit_SD_nb_b, itemtype = "grad")
sd_plink_C_nb <- read.mirt(fit_SD_nb_c, itemtype = "grad")

bi_plink_A_nb <- read.mirt(fit_BI_nb_a, itemtype = "grad")
bi_plink_B_nb <- read.mirt(fit_BI_nb_b, itemtype = "grad")
bi_plink_C_nb <- read.mirt(fit_BI_nb_c, itemtype = "grad")

ci_mods_list <- list(ci_plink_B, ci_plink_A, ci_plink_C)
sd_mods_list <- list(sd_plink_B, sd_plink_A, sd_plink_C)
bi_mods_list <- list(bi_plink_B, bi_plink_A, bi_plink_C)

ci_mods_list_nb <- list(ci_plink_B_nb, ci_plink_A_nb, ci_plink_C_nb)
sd_mods_list_nb <- list(sd_plink_B_nb, sd_plink_A_nb, sd_plink_C_nb)
bi_mods_list_nb <- list(bi_plink_B_nb, bi_plink_A_nb, bi_plink_C_nb)

ci_idx1 <- match(anchor_ci, colnames(CI_CM_full_a))
ci_idx2 <- match(anchor_ci, colnames(CI_CM_full_b))
ci_idx3 <- match(anchor_ci, colnames(CI_CM_full_c))

sd_idx1 <- match(anchor_ci, colnames(SD_CM_full_a))
sd_idx1_ab <- match(anchor_sd_ab, colnames(SD_CM_full_a))
sd_idx1_ac <- match(anchor_sd_ac, colnames(SD_CM_full_a))
sd_idx2 <- match(anchor_sd_ab, colnames(SD_CM_full_b))
sd_idx3 <- match(anchor_sd_ac, colnames(SD_CM_full_c))

sd_idx1 <- match(anchor_ci, colnames(SD_CM_full_a))
sd_idx1_ab <- match(anchor_sd_ab, colnames(SD_CM_full_a))
sd_idx1_ac <- match(anchor_sd_ac, colnames(SD_CM_full_a))

bi_idx1 <- match(anchor_bi, colnames(BI_CM_full_a))
bi_idx1_ab <- match(anchor_bi_ab, colnames(BI_CM_full_a))
bi_idx1_ac <- match(anchor_bi_ac, colnames(BI_CM_full_a))
bi_idx2_bc <- match(anchor_bi_bc, colnames(BI_CM_full_b))   # alt chain only

bi_idx2 <- match(anchor_bi_ab, colnames(BI_CM_full_b))
bi_idx3 <- match(anchor_bi_ac, colnames(BI_CM_full_c))


###all common anchors, matching SD approach of linking A to B, then C to A
###Alternative is B to A, C to B
ci_anchor_ab <- cbind(ci_idx2, ci_idx1)
ci_anchor_ac <- cbind(ci_idx1, ci_idx3)

###Common anchors on A, not B and C,  of linking A to B, then C to A
sd_anchor_ab <- cbind(sd_idx2, sd_idx1_ab)
sd_anchor_ac <- cbind(sd_idx1_ac, sd_idx3)

###Ignoring common items between b and c, matching the above methods of linking A to B, then C to A
bi_anchor_ab <- cbind(bi_idx2, bi_idx1_ab)
bi_anchor_ac <- cbind(bi_idx1_ac, bi_idx3)

ci_common_matrix <- list(ci_anchor_ab, ci_anchor_ac)
sd_common_matrix <- list(sd_anchor_ab, sd_anchor_ac)
bi_common_matrix <- list(bi_anchor_ab, bi_anchor_ac)

# Check on any common matrix - both columns must name the same items
colnames(SD_CM_full_b)[sd_anchor_ab[,1]] == colnames(SD_CM_full_a)[sd_anchor_ab[,2]]

###calibration###

ci_plink_obj <- plink(
  ci_mods_list,
  common = ci_common_matrix,
  rescale = "SL",          # Stocking–Lord
  base.grp = 2             # Form 1 = reference scale
)

sd_plink_obj <- plink(
  sd_mods_list,
  common = sd_common_matrix,
  rescale = "SL",          # Stocking–Lord
  base.grp = 2             # Form 1 = reference scale
)


bi_plink_obj <- plink(
  bi_mods_list,
  common = bi_common_matrix,
  rescale = "SL",          # Stocking–Lord
  base.grp = 2             # Form 1 = reference scale
)

ci_plink_nb_obj <- plink(
  ci_mods_list_nb,
  common = ci_common_matrix,
  rescale = "SL",          # Stocking–Lord
  base.grp = 2             # Form 1 = reference scale
)

sd_plink_nb_obj <- plink(
  sd_mods_list_nb,
  common = sd_common_matrix,
  rescale = "SL",          # Stocking–Lord
  base.grp = 2             # Form 1 = reference scale
)

bi_plink_nb_obj <- plink(
  bi_mods_list_nb,
  common = bi_common_matrix,
  rescale = "SL",          # Stocking–Lord
  base.grp = 2            # Form 1 = reference scale
)

class(sd_plink_obj$pars)
  slotNames(sd_plink_obj$pars)
  str(sd_plink_obj$pars)

ci_rescaled_pars <- ci_plink_obj$pars
sd_rescaled_pars <- sd_plink_obj$pars
bi_rescaled_pars <- bi_plink_obj$pars
ci_rescaled_nb_pars <- ci_plink_nb_obj$pars
sd_rescaled_nb_pars <- sd_plink_nb_obj$pars
bi_rescaled_nb_pars <- bi_plink_nb_obj$pars

#rescaled parameters#
ci_linked_pars <- link.pars(ci_plink_obj)
sd_linked_pars <- link.pars(sd_plink_obj)
bi_linked_pars <- link.pars(bi_plink_obj)
ci_linked_pars_nb <- link.pars(ci_plink_nb_obj)
sd_linked_pars_nb <- link.pars(sd_plink_nb_obj)
bi_linked_pars_nb <- link.pars(bi_plink_nb_obj)


###linking item names###
ci_full_namesA <- colnames(CI_CM_full_a)
ci_full_namesB <- colnames(CI_CM_full_b)
ci_full_namesC <- colnames(CI_CM_full_c)
ci_nb_namesA <- colnames(CI_CM_nb_a)
ci_nb_namesB <- colnames(CI_CM_nb_b)
ci_nb_namesC <- colnames(CI_CM_nb_c)

sd_full_namesA <- colnames(SD_CM_full_a)
sd_full_namesB <- colnames(SD_CM_full_b)
sd_full_namesC <- colnames(SD_CM_full_c)
sd_nb_namesA <- colnames(SD_CM_nb_a)
sd_nb_namesB <- colnames(SD_CM_nb_b)
sd_nb_namesC <- colnames(SD_CM_nb_c)

bi_full_namesA <- colnames(BI_CM_full_a)
bi_full_namesB <- colnames(BI_CM_full_b)
bi_full_namesC <- colnames(BI_CM_full_c)
bi_nb_namesA <- colnames(BI_CM_nb_a)
bi_nb_namesB <- colnames(BI_CM_nb_b)
bi_nb_namesC <- colnames(BI_CM_nb_c)

rownames(ci_linked_pars[[1]]) <- ci_full_namesB
rownames(ci_linked_pars[[2]]) <- ci_full_namesA
rownames(ci_linked_pars[[3]]) <- ci_full_namesC
rownames(ci_linked_pars_nb[[1]]) <- ci_nb_namesB
rownames(ci_linked_pars_nb[[2]]) <- ci_nb_namesA
rownames(ci_linked_pars_nb[[3]]) <- ci_nb_namesC

rownames(sd_linked_pars[[1]]) <- sd_full_namesB
rownames(sd_linked_pars[[2]]) <- sd_full_namesA
rownames(sd_linked_pars[[3]]) <- sd_full_namesC
rownames(sd_linked_pars_nb[[1]]) <- sd_nb_namesB
rownames(sd_linked_pars_nb[[2]]) <- sd_nb_namesA
rownames(sd_linked_pars_nb[[3]]) <- sd_nb_namesC

rownames(bi_linked_pars[[1]]) <- bi_full_namesB
rownames(bi_linked_pars[[2]]) <- bi_full_namesA
rownames(bi_linked_pars[[3]]) <- bi_full_namesC
rownames(bi_linked_pars_nb[[1]]) <- bi_nb_namesB
rownames(bi_linked_pars_nb[[2]]) <- bi_nb_namesA
rownames(bi_linked_pars_nb[[3]]) <- bi_nb_namesC

extract_plink_pars <- function(plink_pars_obj, form_index) {
  # form_data is already a matrix
  pars_mat <- as.data.frame(plink_pars_obj[[form_index]])
  
  # Preserve item names if they exist, otherwise label them Item_1, Item_2...
  if (!is.null(rownames(pars_mat)) && all(rownames(pars_mat) != "")) {
    pars_mat <- pars_mat %>% tibble::rownames_to_column(var = "Item")
  } else {
    pars_mat <- pars_mat %>% mutate(Item = paste0("Item_", row_number()), .before = 1)
  }
  
  return(pars_mat)
}

sl_plink_sheets <- list(
  "CI_Form_A_Base"   = extract_plink_pars(ci_linked_pars, 2),
  "CI_Form_B_Linked" = extract_plink_pars(ci_linked_pars, 1),
  "CI_Form_C_Linked" = extract_plink_pars(ci_linked_pars, 3),
  "CInb_Form_A_Base"   = extract_plink_pars(ci_linked_pars_nb, 2),
  "CInb_Form_B_Linked" = extract_plink_pars(ci_linked_pars_nb, 1),
  "CInb_Form_C_Linked" = extract_plink_pars(ci_linked_pars_nb, 3),
  "SD_Form_A_Base"   = extract_plink_pars(sd_linked_pars, 2),
  "SD_Form_B_Linked" = extract_plink_pars(sd_linked_pars, 1),
  "SD_Form_C_Linked" = extract_plink_pars(sd_linked_pars, 3),
  "SDnb_Form_A_Base"   = extract_plink_pars(sd_linked_pars_nb, 2),
  "SDnb_Form_B_Linked" = extract_plink_pars(sd_linked_pars_nb, 1),
  "SDnb_Form_C_Linked" = extract_plink_pars(sd_linked_pars_nb, 3),
  "BI_Form_A_Base"   = extract_plink_pars(bi_linked_pars, 2),
  "BI_Form_B_Linked" = extract_plink_pars(bi_linked_pars, 1),
  "BI_Form_C_Linked" = extract_plink_pars(bi_linked_pars, 3),
  "BInb_Form_A_Base"   = extract_plink_pars(bi_linked_pars_nb, 2),
  "BInb_Form_B_Linked" = extract_plink_pars(bi_linked_pars_nb, 1),
  "BInb_Form_C_Linked" = extract_plink_pars(bi_linked_pars_nb, 3)
)

write.xlsx(sl_plink_sheets, file = "Linked_IRT_Parameters_SL.xlsx", overwrite = TRUE)

###estimating ability###

link_and_score <- function(fit, data, linked) {
  
  # Get original mirt parameter table
  pars <- mod2values(fit)
  
  # Loop over every item returned by link.pars()
  for (i in seq_len(nrow(linked))) {
    
    item <- rownames(linked)[i]
    
    # link.pars() output:
    # column 1 = discrimination (a)
    # columns 2:5 = GRM thresholds (b1:b4)
    a <- as.numeric(linked[i, 1])
    b_raw <- as.numeric(linked[i, -1])
    b <- b_raw[!is.na(b_raw)]
    
    # Convert GRM a/b to mirt a/d
    d <- -a * b
    
    # Replace the item's parameters
    pars$value[pars$item == item & pars$name == "a1"] <- a
    for (k in seq_along(d)) {
      d_name <- paste0("d", k)
      pars$value[pars$item == item & pars$name == d_name] <- d[k]
    }
  }
  
  # Fix all item parameters
  pars$est[
    pars$name == "a1" | grepl("^d\\d+$", pars$name)
  ] <- FALSE
  
  # Recreate the model using the linked item parameters
  fit_linked <- mirt(
    data = data,
    model = 1,
    itemtype = "graded",
    pars = pars
  )
  
  # Score respondents
  list(
    model = fit_linked,
    ML  = fscores(fit_linked, method = "ML"),
    EAP = fscores(fit_linked, method = "EAP")
  )
}

cif_B <- link_and_score(
  fit = fit_CI_full_b,
  data = CI_CM_full_b,
  linked = ci_linked_pars$group1
)

sdf_B <- link_and_score(
  fit = fit_SD_full_b,
  data = SD_CM_full_b,
  linked = sd_linked_pars$group1
)

bif_B <- link_and_score(
  fit = fit_BI_full_b,
  data = BI_CM_full_b,
  linked = bi_linked_pars$group1
)

cinb_B <- link_and_score(
  fit = fit_CI_nb_b,
  data = CI_CM_nb_b,
  linked = ci_linked_pars_nb$group1
)

sdnb_B <- link_and_score(
  fit = fit_SD_nb_b,
  data = SD_CM_nb_b,
  linked = sd_linked_pars_nb$group1
)

binb_B <- link_and_score(
  fit = fit_BI_nb_b,
  data = BI_CM_nb_b,
  linked = bi_linked_pars_nb$group1
)

#form C#

cif_C <- link_and_score(
  fit = fit_CI_full_c,
  data = CI_CM_full_c,
  linked = ci_linked_pars$group3
)

sdf_C <- link_and_score(
  fit = fit_SD_full_c,
  data = SD_CM_full_c,
  linked = sd_linked_pars$group3
)


bif_C <- link_and_score(
  fit = fit_BI_full_c,
  data = BI_CM_full_c,
  linked = bi_linked_pars$group3
)

cinb_C <- link_and_score(
  fit = fit_CI_nb_c,
  data = CI_CM_nb_c,
  linked = ci_linked_pars_nb$group3
)

sdnb_C <- link_and_score(
  fit = fit_SD_nb_c,
  data = SD_CM_nb_c,
  linked = sd_linked_pars_nb$group3
)

binb_C <- link_and_score(
  fit = fit_BI_nb_c,
  data = BI_CM_nb_c,
  linked = bi_linked_pars_nb$group3
)

###combining thetas###

ci_sl_ml_A <- as.data.frame(fscores(fit_CI_full_a, method = "ML"))
ci_sl_ml_B <- as.data.frame(cif_B$ML)
ci_sl_ml_C <- as.data.frame(cif_C$ML)
ci_sl_eap_A <- as.data.frame(fscores(fit_CI_full_a, method = "EAP"))
ci_sl_eap_B <- as.data.frame(cif_B$EAP)
ci_sl_eap_C <- as.data.frame(cif_C$EAP)

sd_sl_ml_A <- as.data.frame(fscores(fit_SD_full_a, method = "ML"))
sd_sl_ml_B <- as.data.frame(sdf_B$ML)
sd_sl_ml_C <- as.data.frame(sdf_C$ML)
sd_sl_eap_A <- as.data.frame(fscores(fit_SD_full_a, method = "EAP"))
sd_sl_eap_B <- as.data.frame(sdf_B$EAP)
sd_sl_eap_C <- as.data.frame(sdf_C$EAP)

bi_sl_ml_A <- as.data.frame(fscores(fit_BI_full_a, method = "ML"))
bi_sl_ml_B <- as.data.frame(bif_B$ML)
bi_sl_ml_C <- as.data.frame(bif_C$ML)
bi_sl_eap_A <- as.data.frame(fscores(fit_BI_full_a, method = "EAP"))
bi_sl_eap_B <- as.data.frame(bif_B$EAP)
bi_sl_eap_C <- as.data.frame(bif_C$EAP)

cinb_sl_ml_A <- as.data.frame(fscores(fit_CI_nb_a, method = "ML"))
cinb_sl_ml_B <- as.data.frame(cinb_B$ML)
cinb_sl_ml_C <- as.data.frame(cinb_C$ML)
cinb_sl_eap_A <- as.data.frame(fscores(fit_CI_nb_a, method = "EAP"))
cinb_sl_eap_B <- as.data.frame(cinb_B$EAP)
cinb_sl_eap_C <- as.data.frame(cinb_C$EAP)

sdnb_sl_ml_A <- as.data.frame(fscores(fit_SD_nb_a, method = "ML"))
sdnb_sl_ml_B <- as.data.frame(sdnb_B$ML)
sdnb_sl_ml_C <- as.data.frame(sdnb_C$ML)
sdnb_sl_eap_A <- as.data.frame(fscores(fit_SD_nb_a, method = "EAP"))
sdnb_sl_eap_B <- as.data.frame(sdnb_B$EAP)
sdnb_sl_eap_C <- as.data.frame(sdnb_C$EAP)

binb_sl_ml_A <- as.data.frame(fscores(fit_BI_nb_a, method = "ML"))
binb_sl_ml_B <- as.data.frame(binb_B$ML)
binb_sl_ml_C <- as.data.frame(binb_C$ML)
binb_sl_eap_A <- as.data.frame(fscores(fit_BI_nb_a, method = "EAP"))
binb_sl_eap_B <- as.data.frame(binb_B$EAP)
binb_sl_eap_C <- as.data.frame(binb_C$EAP)

###merging###

names(ci_sl_ml_A)[1]  <- "CI_SL_ML"
names(ci_sl_ml_B)[1]  <- "CI_SL_ML"
names(ci_sl_ml_C)[1]  <- "CI_SL_ML"
names(ci_sl_eap_A)[1] <- "CI_SL_EAP"
names(ci_sl_eap_B)[1] <- "CI_SL_EAP"
names(ci_sl_eap_C)[1] <- "CI_SL_EAP"
names(sd_sl_ml_A)[1]  <- "SD_SL_ML"
names(sd_sl_ml_B)[1]  <- "SD_SL_ML"
names(sd_sl_ml_C)[1]  <- "SD_SL_ML"
names(sd_sl_eap_A)[1] <- "SD_SL_EAP"
names(sd_sl_eap_B)[1] <- "SD_SL_EAP"
names(sd_sl_eap_C)[1] <- "SD_SL_EAP"
names(bi_sl_ml_A)[1]  <- "BI_SL_ML"
names(bi_sl_ml_B)[1]  <- "BI_SL_ML"
names(bi_sl_ml_C)[1]  <- "BI_SL_ML"
names(bi_sl_eap_A)[1] <- "BI_SL_EAP"
names(bi_sl_eap_B)[1] <- "BI_SL_EAP"
names(bi_sl_eap_C)[1] <- "BI_SL_EAP"
names(cinb_sl_ml_A)[1]  <- "CInb_SL_ML"
names(cinb_sl_ml_B)[1]  <- "CInb_SL_ML"
names(cinb_sl_ml_C)[1]  <- "CInb_SL_ML"
names(cinb_sl_eap_A)[1] <- "CInb_SL_EAP"
names(cinb_sl_eap_B)[1] <- "CInb_SL_EAP"
names(cinb_sl_eap_C)[1] <- "CInb_SL_EAP"
names(sdnb_sl_ml_A)[1]  <- "SDnb_SL_ML"
names(sdnb_sl_ml_B)[1]  <- "SDnb_SL_ML"
names(sdnb_sl_ml_C)[1]  <- "SDnb_SL_ML"
names(sdnb_sl_eap_A)[1] <- "SDnb_SL_EAP"
names(sdnb_sl_eap_B)[1] <- "SDnb_SL_EAP"
names(sdnb_sl_eap_C)[1] <- "SDnb_SL_EAP"
names(binb_sl_ml_A)[1]  <- "BInb_SL_ML"
names(binb_sl_ml_B)[1]  <- "BInb_SL_ML"
names(binb_sl_ml_C)[1]  <- "BInb_SL_ML"
names(binb_sl_eap_A)[1] <- "BInb_SL_EAP"
names(binb_sl_eap_B)[1] <- "BInb_SL_EAP"
names(binb_sl_eap_C)[1] <- "BInb_SL_EAP"

ci_sl_ml_A$subject_id <- CI_CM_full_a_id$id_work
ci_sl_ml_B$subject_id <- CI_CM_full_b_id$id_work
ci_sl_ml_C$subject_id <- CI_CM_full_c_id$id_work
ci_sl_eap_A$subject_id <- CI_CM_full_a_id$id_work
ci_sl_eap_B$subject_id <- CI_CM_full_b_id$id_work
ci_sl_eap_C$subject_id <- CI_CM_full_c_id$id_work
sd_sl_ml_A$subject_id <- SD_CM_full_a_id$id_work
sd_sl_ml_B$subject_id <- SD_CM_full_b_id$id_work
sd_sl_ml_C$subject_id <- SD_CM_full_c_id$id_work
sd_sl_eap_A$subject_id <- SD_CM_full_a_id$id_work
sd_sl_eap_B$subject_id <- SD_CM_full_b_id$id_work
sd_sl_eap_C$subject_id <- SD_CM_full_c_id$id_work
bi_sl_ml_A$subject_id <- BI_CM_full_a_id$id_work
bi_sl_ml_B$subject_id <- BI_CM_full_b_id$id_work
bi_sl_ml_C$subject_id <- BI_CM_full_c_id$id_work
bi_sl_eap_A$subject_id <- BI_CM_full_a_id$id_work
bi_sl_eap_B$subject_id <- BI_CM_full_b_id$id_work
bi_sl_eap_C$subject_id <- BI_CM_full_c_id$id_work

cinb_sl_ml_A$subject_id <- CI_CM_nb_a_id$id_work
cinb_sl_ml_B$subject_id <- CI_CM_nb_b_id$id_work
cinb_sl_ml_C$subject_id <- CI_CM_nb_c_id$id_work
cinb_sl_eap_A$subject_id <- CI_CM_nb_a_id$id_work
cinb_sl_eap_B$subject_id <- CI_CM_nb_b_id$id_work
cinb_sl_eap_C$subject_id <- CI_CM_nb_c_id$id_work
sdnb_sl_ml_A$subject_id <- SD_CM_nb_a_id$id_work
sdnb_sl_ml_B$subject_id <- SD_CM_nb_b_id$id_work
sdnb_sl_ml_C$subject_id <- SD_CM_nb_c_id$id_work
sdnb_sl_eap_A$subject_id <- SD_CM_nb_a_id$id_work
sdnb_sl_eap_B$subject_id <- SD_CM_nb_b_id$id_work
sdnb_sl_eap_C$subject_id <- SD_CM_nb_c_id$id_work
binb_sl_ml_A$subject_id <- BI_CM_nb_a_id$id_work
binb_sl_ml_B$subject_id <- BI_CM_nb_b_id$id_work
binb_sl_ml_C$subject_id <- BI_CM_nb_c_id$id_work
binb_sl_eap_A$subject_id <- BI_CM_nb_a_id$id_work
binb_sl_eap_B$subject_id <- BI_CM_nb_b_id$id_work
binb_sl_eap_C$subject_id <- BI_CM_nb_c_id$id_work

sl_theta_A <- Reduce(
  function(x, y) merge(x, y, by = "subject_id", all = TRUE),
  list(ci_sl_ml_A, ci_sl_eap_A,
       sd_sl_ml_A, sd_sl_eap_A,
       bi_sl_ml_A, bi_sl_eap_A,
       cinb_sl_ml_A, cinb_sl_eap_A,
       sdnb_sl_ml_A, sdnb_sl_eap_A,
       binb_sl_ml_A, binb_sl_eap_A
       )
)
sl_theta_B <- Reduce(
  function(x, y) merge(x, y, by = "subject_id", all = TRUE),
  list(ci_sl_ml_B, ci_sl_eap_B,
       sd_sl_ml_B, sd_sl_eap_B,
       bi_sl_ml_B, bi_sl_eap_B,
       cinb_sl_ml_B, cinb_sl_eap_B,
       sdnb_sl_ml_B, sdnb_sl_eap_B,
       binb_sl_ml_B, binb_sl_eap_B
  )
)

sl_theta_C <- Reduce(
  function(x, y) merge(x, y, by = "subject_id", all = TRUE),
  list(ci_sl_ml_C, ci_sl_eap_C,
       sd_sl_ml_C, sd_sl_eap_C,
       bi_sl_ml_C, bi_sl_eap_C,
       cinb_sl_ml_C, cinb_sl_eap_C,
       sdnb_sl_ml_C, sdnb_sl_eap_C,
       binb_sl_ml_C, binb_sl_eap_C
  )
)

sl_theta_A$form <- "A"
sl_theta_B$form <- "B"
sl_theta_C$form <- "C"


sl_theta_all <- rbind(sl_theta_A, sl_theta_B, sl_theta_C)

write.csv(sl_theta_all, "SL_theta_estimates.csv", row.names = FALSE)
write_dta(sl_theta_all, "SL_theta_estimates.dta")


############################################
##########Part 5: Bayesian IRT #############
##########Application usin rSTAN ###########
##########Sensitivity Analysis #############
############################################

Sys.unsetenv("R_MAKEVARS_USER")

rstan_options(auto_write = TRUE)
#options(mc.cores = parallel::detectCores())

###configuring R to run STAN###

#Sys.which("make")
#Sys.getenv("PATH")

#pkgbuild::check_build_tools(debug = TRUE)

#dotR <- file.path(Sys.getenv("HOME"), ".R")
#if (!file.exists(dotR)) dir.create(dotR)
#M <- file.path(dotR, "Makevars.win")
#if (!file.exists(M)) file.create(M)
#cat("\nCXX14FLAGS=-O3 -march=native",
#    "CXX14 = $(BINPREF)g++ -m$(WIN) -std=c++1y",
#    file = M, sep = "\n", append = TRUE)

#file.edit(file.path(Sys.getenv("HOME"), ".R", "Makevars.win"))

###replacing with###
#CXX14FLAGS=-O3
#CXX14=$(BINPREF)g++ -m$(WIN) -std=c++1y

####structuring dataM###

#Setting up wide data#

ci_full_wide<-subset(CI_CM_full_id, select = -c(grp_final))
sd_full_wide<-subset(SD_CM_full_id, select = -c(grp_final))
bi_full_wide<-subset(BI_CM_full_id, select = -c(grp_final))               
ci_nb_wide<-subset(CI_CM_nobike_id, select = -c(grp_final))
sd_nb_wide<-subset(SD_CM_nobike_id, select = -c(grp_final))
bi_nb_wide<-subset(BI_CM_nobike_id, select = -c(grp_final))                     

ci_full_wide <- ci_full_wide %>%
  mutate(across(everything(), zap_labels))
ci_nb_wide <- ci_nb_wide %>%
  mutate(across(everything(), zap_labels))

sd_full_wide <- sd_full_wide %>%
  mutate(across(everything(), zap_labels))
sd_nb_wide <- sd_nb_wide %>%
  mutate(across(everything(), zap_labels))

bi_full_wide <- bi_full_wide %>%
  mutate(across(everything(), zap_labels))
bi_nb_wide <- bi_nb_wide %>%
  mutate(across(everything(), zap_labels))

# wide to long format

ci_full_long <- ci_full_wide %>%
  mutate(id_work = row_number()) %>%
  pivot_longer(-id_work, names_to = "item_name", values_to = "response") %>%
  mutate(
    item_id = as.numeric(as.factor(item_name)),
    response = zap_labels(response)
  ) %>%
  filter(!is.na(response)) %>%
  group_by(item_id) %>%
  mutate(y_adj = response - min(response) + 1) %>% 
  ungroup()

sd_full_long <- sd_full_wide %>%
  mutate(id_work = row_number()) %>%
  pivot_longer(-id_work, names_to = "item_name", values_to = "response") %>%
  mutate(
    item_id = as.numeric(as.factor(item_name)),
    response = zap_labels(response)
  ) %>%
  filter(!is.na(response)) %>%
  group_by(item_id) %>%
  mutate(y_adj = response - min(response) + 1) %>% 
  ungroup()

bi_full_long <- bi_full_wide %>%
  mutate(id_work = row_number()) %>%
  pivot_longer(-id_work, names_to = "item_name", values_to = "response") %>%
  mutate(
    item_id = as.numeric(as.factor(item_name)),
    response = zap_labels(response)
  ) %>%
  filter(!is.na(response)) %>%
  group_by(item_id) %>%
  mutate(y_adj = response - min(response) + 1) %>% 
  ungroup()

ci_nb_long <- ci_nb_wide %>%
  mutate(id_work = row_number()) %>%
  pivot_longer(-id_work, names_to = "item_name", values_to = "response") %>%
  mutate(
    item_id = as.numeric(as.factor(item_name)),
    response = zap_labels(response)
  ) %>%
  filter(!is.na(response)) %>%
  group_by(item_id) %>%
  mutate(y_adj = response - min(response) + 1) %>% 
  ungroup()

sd_nb_long <- sd_nb_wide %>%
  mutate(id_work = row_number()) %>%
  pivot_longer(-id_work, names_to = "item_name", values_to = "response") %>%
  mutate(
    item_id = as.numeric(as.factor(item_name)),
    response = zap_labels(response)
  ) %>%
  filter(!is.na(response)) %>%
  group_by(item_id) %>%
  mutate(y_adj = response - min(response) + 1) %>% 
  ungroup()

bi_nb_long <- bi_nb_wide %>%
  mutate(id_work = row_number()) %>%
  pivot_longer(-id_work, names_to = "item_name", values_to = "response") %>%
  mutate(
    item_id = as.numeric(as.factor(item_name)),
    response = zap_labels(response)
  ) %>%
  filter(!is.na(response)) %>%
  group_by(item_id) %>%
  mutate(y_adj = response - min(response) + 1) %>% 
  ungroup()

cif_K_per_item <- ci_full_long %>%
  group_by(item_id) %>%
  summarize(K = max(y_adj)) %>%
  pull(K)
sdf_K_per_item <- sd_full_long %>%
  group_by(item_id) %>%
  summarize(K = max(y_adj)) %>%
  pull(K)
bif_K_per_item <- bi_full_long %>%
  group_by(item_id) %>%
  summarize(K = max(y_adj)) %>%
  pull(K)

cinb_K_per_item <- ci_nb_long %>%
  group_by(item_id) %>%
  summarize(K = max(y_adj)) %>%
  pull(K)
sdnb_K_per_item <- sd_nb_long %>%
  group_by(item_id) %>%
  summarize(K = max(y_adj)) %>%
  pull(K)
binb_K_per_item <- bi_nb_long %>%
  group_by(item_id) %>%
  summarize(K = max(y_adj)) %>%
  pull(K)

cif_stan_data <- list(
  N = nrow(ci_full_long),
  I = max(ci_full_long$item_id),
  J = max(ci_full_long$id_work),
  K_max = max(cif_K_per_item),
  item = ci_full_long$item_id,
  person = ci_full_long$id_work,
  y = ci_full_long$y_adj,
  K_items = cif_K_per_item
)
sdf_stan_data <- list(
  N = nrow(sd_full_long),
  I = max(sd_full_long$item_id),
  J = max(sd_full_long$id_work),
  K_max = max(sdf_K_per_item),
  item = sd_full_long$item_id,
  person = sd_full_long$id_work,
  y = sd_full_long$y_adj,
  K_items = sdf_K_per_item
)
bif_stan_data <- list(
  N = nrow(bi_full_long),
  I = max(bi_full_long$item_id),
  J = max(bi_full_long$id_work),
  K_max = max(bif_K_per_item),
  item = bi_full_long$item_id,
  person = bi_full_long$id_work,
  y = bi_full_long$y_adj,
  K_items = bif_K_per_item
)

cinb_stan_data <- list(
  N = nrow(ci_nb_long),
  I = max(ci_nb_long$item_id),
  J = max(ci_nb_long$id_work),
  K_max = max(cinb_K_per_item),
  item = ci_nb_long$item_id,
  person = ci_nb_long$id_work,
  y = ci_nb_long$y_adj,
  K_items = cinb_K_per_item
)
sdnb_stan_data <- list(
  N = nrow(sd_nb_long),
  I = max(sd_nb_long$item_id),
  J = max(sd_nb_long$id_work),
  K_max = max(sdnb_K_per_item),
  item = sd_nb_long$item_id,
  person = sd_nb_long$id_work,
  y = sd_nb_long$y_adj,
  K_items = sdnb_K_per_item
)
binb_stan_data <- list(
  N = nrow(bi_nb_long),
  I = max(bi_nb_long$item_id),
  J = max(bi_nb_long$id_work),
  K_max = max(binb_K_per_item),
  item = bi_nb_long$item_id,
  person = bi_nb_long$id_work,
  y = bi_nb_long$y_adj,
  K_items = binb_K_per_item
)

###saving stan model###

stancode <- r"(
  data {
    int<lower=1> N;                       // Total number of observed responses
    int<lower=1> I;                       // Number of items
    int<lower=1> J;                       // Number of persons
    int<lower=1> K_max;                   // Max categories across all items
    
    array[N] int<lower=1, upper=I> item;   // Item ID per response
    array[N] int<lower=1, upper=J> person; // Person ID per response
    array[N] int<lower=1, upper=K_max> y;  // Responses (Must start at 1!)
    array[I] int<lower=2> K_items;         // Categories per item
  }
  
  parameters {
    vector[J] theta;                      // Person latent traits
    vector<lower=0>[I] alpha;             // Discrimination parameters
    array[I] ordered[K_max - 1] kappa;    // Thresholds
  }
  
  model {
    // Priors
    theta ~ std_normal();
    alpha ~ lognormal(0, 0.5);
    
    for (i in 1:I) {
      // Standard normal prior on active thresholds
      kappa[i, 1:(K_items[i] - 1)] ~ normal(0, 3);
      
      // Regularize unused thresholds to prevent divergent transitions
      if (K_items[i] < K_max) {
        kappa[i, K_items[i]:(K_max - 1)] ~ normal(10, 0.1);
      }
    }
    
    // Likelihood
    for (n in 1:N) {
      int i = item[n];
      int p = person[n];
      int k_item = K_items[i];
      
      // Explicit slice for active item thresholds
      vector[k_item - 1] active_kappa = kappa[i, 1:(k_item - 1)];
      
      y[n] ~ ordered_logistic(alpha[i] * theta[p], active_kappa);
    }
  }

)"

writeLines(stancode, "grm_flexible.stan")


cif_fit_stan <- stan(
  file = "grm_flexible.stan", 
  data = cif_stan_data,
  iter = 4000,
  warmup = 2000,
  chains = 4,
  cores = parallel::detectCores()
)

sdf_fit_stan <- stan(
  file = "grm_flexible.stan", 
  data = sdf_stan_data,
  iter = 4000,
  warmup = 2000,
  chains = 4,
  cores = parallel::detectCores()
)
bif_fit_stan <- stan(
  file = "grm_flexible.stan", 
  data = bif_stan_data,
  iter = 4000,
  warmup = 2000,
  chains = 4,
  cores = parallel::detectCores()
)

cinb_fit_stan <- stan(
  file = "grm_flexible.stan", 
  data = cinb_stan_data,
  iter = 4000,
  warmup = 2000,
  chains = 4,
  cores = parallel::detectCores()
)
sdnb_fit_stan <- stan(
  file = "grm_flexible.stan", 
  data = sdnb_stan_data,
  iter = 4000,
  warmup = 2000,
  chains = 4,
  cores = parallel::detectCores()
)
binb_fit_stan <- stan(
  file = "grm_flexible.stan", 
  data = binb_stan_data,
  iter = 4000,
  warmup = 2000,
  chains = 4,
  cores = parallel::detectCores()
)

cif_item_summary <- summary(cif_fit_stan, pars = c("alpha", "kappa"))$summary
sdf_item_summary <- summary(sdf_fit_stan, pars = c("alpha", "kappa"))$summary
bif_item_summary <- summary(bif_fit_stan, pars = c("alpha", "kappa"))$summary
cinb_item_summary <- summary(cinb_fit_stan, pars = c("alpha", "kappa"))$summary
sdnb_item_summary <- summary(sdnb_fit_stan, pars = c("alpha", "kappa"))$summary
binb_item_summary <- summary(binb_fit_stan, pars = c("alpha", "kappa"))$summary

# Function: item parameter extraction #

extract_item_parameters <- function(
    fit_object,
    wide_data,
    long_data,
    K_per_item
){
  post <- rstan::extract(fit_object)
  
  # Item names
  item_names <- levels(as.factor(long_data$item_name))
  
  # Alpha
  alpha_mean <- apply(post$alpha, 2, mean)
  alpha_sd   <- apply(post$alpha, 2, sd)
  
  # Thresholds
  # change to  ->  divide by alpha draw by draw, then average
  b_draws    <- sweep(post$kappa, c(1, 2), post$alpha, "/")
  kappa_mean <- apply(b_draws, c(2, 3), mean)
  # Keeping the name kappa_mean leaves the rest of the function unchanged.
  
  item_parameters <- data.frame(
    item_id = 1:length(alpha_mean),
    item_name = item_names,
    a = alpha_mean,
    a_SD = alpha_sd
  )
  
  kappa_df <- as.data.frame(kappa_mean)
  colnames(kappa_df) <-
    paste0("b", 1:ncol(kappa_df))
  item_parameters <-
    cbind(item_parameters, kappa_df)
  
  # Remove artificial unused thresholds
  for(i in 1:nrow(item_parameters)){
    n_thresholds <- K_per_item[i]-1
    if(n_thresholds < ncol(kappa_df)){
      item_parameters[i,
                      paste0("b",
                             (n_thresholds+1):ncol(kappa_df))
      ] <- NA
    }
  }
  return(item_parameters)
}


### Extract item parameters ###
CI_full_stan_par <- extract_item_parameters(
  cif_fit_stan,
  ci_full_wide,
  ci_full_long,
  cif_K_per_item
)

SD_full_stan_par <- extract_item_parameters(
  sdf_fit_stan,
  sd_full_wide,
  sd_full_long,
  sdf_K_per_item
)

BI_full_stan_par <- extract_item_parameters(
  bif_fit_stan,
  bi_full_wide,
  bi_full_long,
  bif_K_per_item
)

CI_nb_stan_par <- extract_item_parameters(
  cinb_fit_stan,
  ci_nb_wide,
  ci_nb_long,
  cinb_K_per_item
)

SD_nb_stan_par <- extract_item_parameters(
  sdnb_fit_stan,
  sd_nb_wide,
  sd_nb_long,
  sdnb_K_per_item
)

BI_nb_stan_par <- extract_item_parameters(
  binb_fit_stan,
  bi_nb_wide,
  bi_nb_long,
  binb_K_per_item
)

###

CI_full_stan_par <- CI_full_stan_par %>%
  mutate(scale = "CI_full_stan")
CI_nb_stan_par <- CI_nb_stan_par %>%
  mutate(scale = "CI_nobike_stan")

SD_full_stan_par <- SD_full_stan_par %>%
  mutate(scale = "SD_full_stan")
SD_nb_stan_par <- SD_nb_stan_par %>%
  mutate(scale = "SD_nobike_stan")

BI_full_stan_par <- BI_full_stan_par %>%
  mutate(scale = "BI_full_stan")
BI_nb_stan_par <- BI_nb_stan_par %>%
  mutate(scale = "BI_nobike_stan")

###export to excel###
STANirt_par_sheets <- list(
  "STAN_CI_Full"  = CI_full_stan_par,
  "STAN_SD_Full"  = SD_full_stan_par,
  "STAN_BI_Full"  = BI_full_stan_par,
  "STAN_CI_nobike"  = CI_nb_stan_par,
  "STAN_SD_nobike"  = SD_nb_stan_par,
  "STAN_BI_nobike"  = BI_nb_stan_par
)

write.xlsx(STANirt_par_sheets, file = "STANIRT_Item_Parameters.xlsx", overwrite = TRUE)


### Theta extraction ###

extract_theta <- function(
    fit_object,
    subject_ids,
    scale_name
){
  post <- rstan::extract(fit_object)
  theta_mean <-
    apply(post$theta,2,mean)
  theta_sd <-
    apply(post$theta,2,sd)
  
  data.frame(
    subject_id = subject_ids,
    theta = theta_mean,
    theta_SD = theta_sd,
    scale = scale_name
  )
}

ci_ids <- rownames(ci_full_wide)
sd_ids <- rownames(sd_full_wide)
bi_ids <- rownames(bi_full_wide)
ci_nb_ids <- rownames(ci_nb_wide)
sd_nb_ids <- rownames(sd_nb_wide)
bi_nb_ids <- rownames(bi_nb_wide)

CI_stan_theta <- extract_theta(
  cif_fit_stan,
  ci_ids,
  "CI"
)

SD_stan_theta <- extract_theta(
  sdf_fit_stan,
  sd_ids,
  "SD"
)

BI_stan_theta <- extract_theta(
  bif_fit_stan,
  bi_ids,
  "BI"
)

CInb_stan_theta <- extract_theta(
  cinb_fit_stan,
  ci_nb_ids,
  "CI"
)

SDnb_stan_theta <- extract_theta(
  sdnb_fit_stan,
  sd_nb_ids,
  "SD"
)

BInb_stan_theta <- extract_theta(
  binb_fit_stan,
  bi_nb_ids,
  "BI"
)

############################################################

names(CI_stan_theta)[2:4] <- c("CI_stan", "CI_stan_sd", "CI_scale")
names(SD_stan_theta)[2:4] <- c("SD_stan", "SD_stan_sd", "SD_scale")
names(BI_stan_theta)[2:4] <- c("BI_stan", "BI_stan_sd", "BI_scale")
names(CInb_stan_theta)[2:4] <- c("CInb_stan", "CInb_stan_sd", "CInb_scale")
names(SDnb_stan_theta)[2:4] <- c("SDnb_stan", "SDnb_stan_sd", "SDnb_scale")
names(BInb_stan_theta)[2:4] <- c("BInb_stan", "BInb_stan_sd", "BInb_scale")

STAN_theta_all <- Reduce(
  function(x, y) merge(x, y, by = "subject_id", all = TRUE),
  list(CI_stan_theta, SD_stan_theta, BI_stan_theta,
       CInb_stan_theta, SDnb_stan_theta, BInb_stan_theta
  )
)

write.csv(STAN_theta_all, "STANIRT_theta_estimates.csv", row.names = FALSE)
write_dta(STAN_theta_all, "STANIRT_theta_estimates.dta")

###################################################
##################Export Thetas####################
###################################################

#Complete data###
nomiss_ml_CM_f <- fscores(fit_CM_full, method = 'ML')
nomiss_eap_CM_f <- fscores(fit_CM_full, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)

nomiss_ml_CM_nb <- fscores(fit_CM_nb, method = 'ML')
nomiss_eap_CM_nb <- fscores(fit_CM_nb, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)

###FIML###
sd_ml_fiml <- fscores(fit_SD_full, method = 'ML', full.scores = TRUE)
sd_eap_fiml <- fscores(fit_SD_full, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)
sd_nb_ml_fiml <- fscores(fit_SD_nb, method = 'ML', full.scores = TRUE)
sd_nb_eap_fiml <- fscores(fit_SD_nb, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)

ci_ml_fiml <- fscores(fit_CI_full, method = 'ML', full.scores = TRUE)
ci_eap_fiml <- fscores(fit_CI_full, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)
ci_nb_ml_fiml <- fscores(fit_CI_nb, method = 'ML', full.scores = TRUE)
ci_nb_eap_fiml <- fscores(fit_CI_nb, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)

bi_ml_fiml <- fscores(fit_BI_full, method = 'ML', full.scores = TRUE)
bi_eap_fiml <- fscores(fit_BI_full, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)
bi_nb_ml_fiml <- fscores(fit_BI_nb, method = 'ML', full.scores = TRUE)
bi_nb_eap_fiml <- fscores(fit_BI_nb, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)

###Multi Group###
sd_ml_mg <- fscores(sd_mg_fit, method = 'ML', full.scores = TRUE)
sd_eap_mg <- fscores(sd_mg_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)
sd_nb_ml_mg <- fscores(sd_mg_nb_fit, method = 'ML', full.scores = TRUE)
sd_nb_eap_mg <- fscores(sd_mg_nb_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)

ci_ml_mg <- fscores(ci_mg_fit, method = 'ML', full.scores = TRUE)
ci_eap_mg <- fscores(ci_mg_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)
ci_nb_ml_mg <- fscores(ci_mg_nb_fit, method = 'ML', full.scores = TRUE)
ci_nb_eap_mg <- fscores(ci_mg_nb_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)

bi_ml_mg <- fscores(bi_mg_fit, method = 'ML', full.scores = TRUE)
bi_eap_mg <- fscores(bi_mg_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)
bi_nb_ml_mg <- fscores(bi_mg_nb_fit, method = 'ML', full.scores = TRUE)
bi_nb_eap_mg <- fscores(bi_mg_nb_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)

###
sd_ml_sl <- fscores(sd_mg_fit, method = 'ML', full.scores = TRUE)
sd_eap_sl <- fscores(sd_mg_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)
sd_nb_ml_sl <- fscores(sd_mg_nb_fit, method = 'ML', full.scores = TRUE)
sd_nb_eap_sl <- fscores(sd_mg_nb_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)

ci_ml_sl <- fscores(ci_mg_fit, method = 'ML', full.scores = TRUE)
ci_eap_sl <- fscores(ci_mg_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)
ci_nb_ml_sl <- fscores(ci_mg_nb_fit, method = 'ML', full.scores = TRUE)
ci_nb_eap_sl <- fscores(ci_mg_nb_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)

bi_ml_sl <- fscores(bi_mg_fit, method = 'ML', full.scores = TRUE)
bi_eap_sl <- fscores(bi_mg_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)
bi_nb_ml_sl <- fscores(bi_mg_nb_fit, method = 'ML', full.scores = TRUE)
bi_nb_eap_sl <- fscores(bi_mg_nb_fit, method = 'EAP', full.scores = TRUE, full.scores.SE = TRUE)


# 2. Combine into a single table

nomiss_scores <- data.frame(
  subject_id = CI_CM_full_id$id_work,
  nonmiss_EAP = nomiss_eap_CM_f[,1],
  nonmiss_SEEAP    = nomiss_eap_CM_f[,2],
  nonmiss_ML  = nomiss_ml_CM_f[,1],
  nonmiss_nb_EAP = nomiss_eap_CM_nb[,1],
  nonmiss_nb_SEEAP    = nomiss_eap_CM_nb[,2],
  nonmiss_nb_ML  = nomiss_ml_CM_nb[,1]
)

#####

ci_fiml_scores <- data.frame(
  subject_id = CI_CM_full_id$id_work,
  CI_fiml_EAP = ci_eap_fiml[,1],
  CI_fiml_SE_EAP = ci_eap_fiml[,2],
  CI_fiml_ML  = ci_ml_fiml[,1],
  CI_fiml_nb_EAP = ci_nb_eap_fiml[,1],
  CI_fiml_nb_SE_EAP = ci_nb_eap_fiml[,2],
  CI_fiml_nb_ML  = ci_nb_ml_fiml[,1]
)

sd_fiml_scores <- data.frame(
  subject_id = SD_CM_full_id$id_work,
  SD_fiml_EAP = sd_eap_fiml[,1],
  SD_fiml_SE_EAP = sd_eap_fiml[,2],
  SD_fiml_ML  = sd_ml_fiml[,1],
  SD_fiml_nb_EAP = sd_nb_eap_fiml[,1],
  SD_fiml_nb_SE_EAP  = sd_nb_eap_fiml[,2],
  SD_fiml_nb_ML  = sd_nb_ml_fiml[,1]
)

bi_fiml_scores <- data.frame(
  subject_id = BI_CM_full_id$id_work,
  BI_fiml_EAP = bi_eap_fiml[,1],
  BI_fiml_SE_EAP = bi_eap_fiml[,2],
  BI_fiml_ML  = bi_ml_fiml[,1],
  BI_fiml_nb_EAP = bi_nb_eap_fiml[,1],
  BI_fiml_nb_SE_EAP  = bi_nb_eap_fiml[,2],
  BI_fiml_nb_ML  = bi_nb_ml_fiml[,1]
)

###

ci_mg_scores <- data.frame(
  subject_id = CI_CM_full_id$id_work,
  CI_MG_EAP = ci_eap_mg[,1],
  CI_MG_SE_EAP    = ci_eap_mg[,2],
  CI_MG_ML  = ci_ml_mg[,1],
  CI_MG_nb_EAP = ci_nb_eap_mg[,1],
  CI_MG_nb_SE_EAP    = ci_nb_eap_mg[,2],
  CI_MG_nb_ML  = ci_nb_ml_mg[,1]
)

sd_mg_scores <- data.frame(
  subject_id = SD_CM_full_id$id_work,
  SD_MG_EAP = sd_eap_mg[,1],
  SD_MG_SE_EAP  = sd_eap_mg[,2],
  SD_MG_ML  = sd_ml_mg[,1],
  SD_MG_nb_EAP = sd_nb_eap_mg[,1],
  SD_MG_nb_SE_EAP    = sd_nb_eap_mg[,2],
  SD_MG_nb_ML  = sd_nb_ml_mg[,1]
)

bi_mg_scores <- data.frame(
  subject_id = BI_CM_full_id$id_work,
  BI_MG_EAP = bi_eap_mg[,1],
  BI_MG_SE_EAP  = bi_eap_mg[,2],
  BI_MG_ML  = bi_ml_mg[,1],
  BI_MG_nb_EAP = bi_nb_eap_mg[,1],
  BI_MG_nb_SE_EAP = bi_nb_eap_mg[,2],
  BI_MG_nb_ML  = bi_nb_ml_mg[,1]
)

###STAN_theta_all was exported to separate excel file###

theta_scores <- list(nomiss_scores, 
                     ci_fiml_scores, sd_fiml_scores, bi_fiml_scores,
                     ci_mg_scores, sd_mg_scores, bi_mg_scores,
                     sl_theta_all) %>%
  reduce(full_join, by = "subject_id")


write.csv(theta_scores, "CM_Theta_Estimates.csv", row.names = FALSE)
write_dta(theta_scores, "CM_Theta_Estimates.dta")

###################
###Saving models###
###################

dir.create("saved_models", showWarnings = FALSE)

saveRDS(fit_CM_full, "saved_models/fit_CM_full.rds")
saveRDS(fit_CM_nb,  "saved_models/fit_CM_nb.rds")
saveRDS(nonmiss_fit_stan, "saved_models/nonmiss_fit_stan.rds")
saveRDS(nonmiss_nb_fit_stan, "saved_models/nonmiss_nb_fit_stan.rds")

saveRDS(fit_SD_full, "saved_models/fit_SD_full.rds")
saveRDS(fit_SD_nb, "saved_models/fit_SD_nb.rds")
saveRDS(fit_CI_full, "saved_models/fit_CI_full.rds")
saveRDS(fit_CI_nb, "saved_models/fit_CI_nb.rds")
saveRDS(fit_BI_full, "saved_models/fit_BI_full.rds")
saveRDS(fit_BI_nb, "saved_models/fit_BI_nb.rds")
        
saveRDS(ci_mg_fit, "saved_models/ci_mg_fit.rds")
saveRDS(ci_mg_nb_fit, "saved_models/ci_mg_nb_fit.rds")
saveRDS(sd_mg_fit, "saved_models/sd_mg_fit.rds")
saveRDS(sd_mg_nb_fit, "saved_models/sd_mg_nb_fit.rds")
saveRDS(bi_mg_fit, "saved_models/bi_mg_fit.rds")
saveRDS(bi_mg_nb_fit, "saved_models/bi_mg_nb_fit.rds")

saveRDS(cif_fit_stan, "saved_models/cif_fit_stan.rds")
saveRDS(sdf_fit_stan, "saved_models/sdf_fit_stan.rds")
saveRDS(bif_fit_stan, "saved_models/bif_fit_stan.rds")
saveRDS(cinb_fit_stan, "saved_models/cinb_fit_stan.rds")
saveRDS(sdnb_fit_stan, "saved_models/sdnb_fit_stan.rds")
saveRDS(binb_fit_stan, "saved_models/binb_fit_stan.rds")

saveRDS(ci_plink_obj, "saved_models/ci_plink_obj.rds")
saveRDS(sd_plink_obj, "saved_models/sd_plink_obj.rds")
saveRDS(bi_plink_obj, "saved_models/bi_plink_obj.rds")
saveRDS(ci_plink_nb_obj, "saved_models/ci_plink_nb_obj.rds")
saveRDS(sd_plink_nb_obj, "saved_models/sd_plink_nb_obj.rds")
saveRDS(bi_plink_nb_obj, "saved_models/bi_plink_nb_obj.rds")
saveRDS(ci_plink_alt_obj, "saved_models/ci_plink_alt_obj.rds")
saveRDS(bi_plink_alt_obj, "saved_models/bi_plink_alt_obj.rds")
