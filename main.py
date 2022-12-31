import math
import json
import calendar
import pandas
import pvlib
from mpl_toolkits import mplot3d
import matplotlib.pyplot as plt

SHOW_PLOTS = False # Set to True to show plots
TRY_ZENITH = False # Set to True to try use zenith angle to calculate clearness index (incorrect)

# Given start and end angles
DATA_START = 48
DATA_END = 71

LOCALE = "Europe/Rome"

# months of interest; January, February, March, December
MONTHS_OF_INTEREST = [1, 2, 3, 12] 
MONTH_NUMBER_TO_STR = {1: "January", 2: "February", 3: "March", 12: "December"}
MONTH_STR_TO_NUMBER = {"January": 1, "February": 2, "March": 3, "December": 12}
MONTH_NAMES = ["January", "February", "March", "December"]
MONTH_NAMES_TO_PLOTPOS = {"January": 1, "February": 2, "March": 3, "December": 0}

# values of interest; H(h)_m, H(i)_m, Hb(n)_m ; 
# H(h)_m = Global horizontal irradiance, 
# H(i)_m = Direct normal irradiance, 
# Hb(n)_m = Global irradiance by tilt angle
VALUES_OF_INTEREST = ["H(h)_m", "H(i)_m", "Hb(n)_m"] 

# Loads the data from the json files
def load_data():
	name = "./data/Monthlydata_42.000_12.215_SA2_2013_2020-"

	datasets = []
	for i in range(DATA_START, DATA_END+1):
		fname = name + str(i) + ".json"
		with open(fname) as f:
			datasets.append(json.load(f))

	return datasets
	
# Parses the data into a more usable format
def data_parse(datasets): # {angle_num: {month_str: {value_num: average}}}
	months_averaged_by_angle = {} # {angle_num: {month_str: {value_num: average}}}

	for dataset in datasets:
		angle = dataset["inputs"]["plane"]["fixed_inclined"]["slope"]["value"]

		year_count = dataset["inputs"]["meteo_data"]["year_max"] - dataset["inputs"]["meteo_data"]["year_min"] + 1

		months_averaged_by_angle[angle] = {}
		for month_name in MONTH_NAMES:
			months_averaged_by_angle[angle][month_name] = {}
			for j in VALUES_OF_INTEREST:
				months_averaged_by_angle[angle][month_name][j] = 0

		for month in dataset["outputs"]["monthly"]:	
			if month["month"] in MONTHS_OF_INTEREST:
				month_name = MONTH_NUMBER_TO_STR[month["month"]]
				for j in VALUES_OF_INTEREST:
					months_averaged_by_angle[angle][month_name][j] += month[j]

		for month_name in MONTH_NAMES:
			for j in VALUES_OF_INTEREST:
				months_averaged_by_angle[angle][month_name][j] /= year_count

	if SHOW_PLOTS:
		#using matplotlib to plot the data in 3d
		fig = plt.figure()
		ax = plt.axes(projection='3d')
		ax.set_xlabel('December -> March')
		ax.set_ylabel('Tilt Angle')
		ax.set_zlabel('H(i) (kWh/m^2)')
		for angle in months_averaged_by_angle:
			for month in months_averaged_by_angle[angle]:
				ax.scatter(
					MONTH_NAMES_TO_PLOTPOS[month], 
					angle, 
					months_averaged_by_angle[angle][month]["H(i)_m"], 
					color='red'
				)
		plt.show()

	return months_averaged_by_angle

# Calculates the optimal PV angle for the given months
def calculate_optimal_angle(months_averaged_by_angle):

	total_by_angle = {}
	for angle in months_averaged_by_angle:
		total_by_angle[angle] = {}
		for j in VALUES_OF_INTEREST:
			total_by_angle[angle][j] = 0
	
	for angle in months_averaged_by_angle:
		for j in VALUES_OF_INTEREST:
			for month in months_averaged_by_angle[angle]:
				total_by_angle[angle][j] += months_averaged_by_angle[angle][month][j]

	for angle in total_by_angle:
		for j in VALUES_OF_INTEREST:
			total_by_angle[angle][j] /= len(months_averaged_by_angle[angle])

	if SHOW_PLOTS:
		#using matplotlib to plot the data in 2d
		fig = plt.figure()
		ax = plt.axes()
		ax.set_xlabel('Tilt Angle')
		ax.set_ylabel('H(i) (kWh/m^2)')
		for angle in total_by_angle:
			ax.scatter(angle, total_by_angle[angle]["H(i)_m"], color='red')
		plt.show()

	optimal_angle = 0
	optimal_value = 0
	for angle in total_by_angle:
		if total_by_angle[angle]["H(i)_m"] > optimal_value:
			optimal_value = total_by_angle[angle]["H(i)_m"]
			optimal_angle = angle

	print("For a winter house, the optimal PV angle is:")
	print("Optimal PV tilt angle: " + str(optimal_angle) + " degrees")
	print("Optimal average monthly energy per square meter of PV: " + str(math.floor(optimal_value+.5)) + " kWh/m^2")
	print("\n")

	return optimal_angle, optimal_value

# Calculate total extra terrestrial radiation for each month of the year
def calculate_extraterrestial_irradiance(start_year, end_year):
	extr_irrad = {}
	for month in MONTHS_OF_INTEREST:
		extr_irrad[month] = 0
		for year in range(start_year, end_year+1):
			for day in range(1, calendar.monthrange(year, month)[1]+1):
				extr_irrad[month] += pvlib.irradiance.get_extra_radiation(pandas.to_datetime(str(year)+"-"+str(month)+"-"+str(day), format="%Y-%m-%d", errors="coerce")) * 24 / 1000 # convert from W/m^2 to kWh/m^2

	for month in extr_irrad:
		extr_irrad[month] /= (end_year - start_year + 1)

	print("Total extra terrestrial radiation for each month of the year:")
	for month in extr_irrad:
		print(MONTH_NUMBER_TO_STR[month] + ": " + str(math.floor(extr_irrad[month]+.5)) + " kWh/m^2")

	print("\n")

	return extr_irrad

# Calculate the clearness index for each month of the year
def calculate_clearness_index_per_month(months_averaged_by_angle, extr_irrad, start_year, end_year, optimal_angle, latitude, longitude):
	clearness_index_per_month = {}
	
	if TRY_ZENITH:
		for month_str in MONTH_NAMES:
			month_num = MONTH_STR_TO_NUMBER[month_str]
			clearness_index_per_month[month_str] = 0

			for year in range(start_year, end_year+1):
				month_day_count = calendar.monthrange(year, month_num)[1]

				for day in range(1, month_day_count+1):
					DatetimeIndex = pandas.DatetimeIndex([str(year)+"-"+str(month_str)+"-"+str(day)])#

					DatetimeIndex = DatetimeIndex.tz_localize("Europe/Rome")

					dayofyear = DatetimeIndex.dayofyear

					ghi = months_averaged_by_angle[optimal_angle][month_str]["H(h)_m"]

					index = 0


					solar_zenith_angle = pvlib.solarposition.solar_zenith_analytical(
						latitude = latitude,
						hourangle = pvlib.solarposition.hour_angle(
							times = DatetimeIndex,
							longitude = longitude,
							equation_of_time = pvlib.solarposition.equation_of_time_pvcdrom(
								dayofyear=dayofyear
							),
						),
						declination = pvlib.solarposition.declination_spencer71(dayofyear)
					)

					index = pvlib.irradiance.clearness_index(
						ghi = ghi * 1000 / month_day_count, # convert from kWh/m^2 to W/m^2
						solar_zenith = solar_zenith_angle,
						extra_radiation = extr_irrad[month_num]
					)

					index = index.values[0]

					clearness_index_per_month[month_str] += index

			clearness_index_per_month[month_str] /= (end_year - start_year + 1) * month_day_count

			print("Clearness index for " + month_str + ": " + str(clearness_index_per_month[month_str]))

	else:
		for month_str in MONTH_NAMES:
			month_num = MONTH_STR_TO_NUMBER[month_str]
			month_day_count = calendar.monthrange(start_year, month_num)[1]
			
			ghi = months_averaged_by_angle[optimal_angle][month_str]["H(i)_m"]
			gei = extr_irrad[month_num]

			index = ghi / gei

			print("Clearness index for " + month_str + ": " + str(index))

			clearness_index_per_month[month_str] = index

	print("\n")

	return clearness_index_per_month

def main():
	print("\n")
	
	datasets = load_data()

	months_averaged_by_angle = data_parse(datasets)

	optimal_angle, optimal_value = calculate_optimal_angle(months_averaged_by_angle)

	meteo_data = datasets[0]["inputs"]["meteo_data"]
	location_data = datasets[0]["inputs"]["location"]

	start_year = meteo_data["year_min"]
	end_year = meteo_data["year_max"] 

	latitude = location_data["latitude"]
	longitude = location_data["longitude"]

	extr_irrad = calculate_extraterrestial_irradiance(start_year, end_year)

	clearness_index_per_month = calculate_clearness_index_per_month(months_averaged_by_angle, extr_irrad, start_year, end_year, optimal_angle, latitude, longitude)

if __name__ == "__main__":
	main()