import math
import json
from mpl_toolkits import mplot3d
import matplotlib.pyplot as plt

SHOW_PLOTS = False

# Given start and end angles
DATA_START = 48
DATA_END = 71

# months of interest; January, February, March, December
MONTHS_OF_INTEREST = [1, 2, 3, 12] 
MONTH_TO_NUMBER = {1: "January", 2: "February", 3: "March", 12: "December"}
MONTH_NAMES = ["January", "February", "March", "December"]
MONTH_NAMES_TO_PLOTPOS = {"January": 1, "February": 2, "March": 3, "December": 0}

# values of interest; H(h)_m, H(i)_m, Hb(n)_m ; 
# H(h)_m = Global horizontal irradiance, 
# H(i)_m = Direct normal irradiance, 
# Hb(n)_m = Global irradiance by tilt angle
VALUES_OF_INTEREST = ["H(h)_m", "H(i)_m", "Hb(n)_m"] 

# Calculates extraterrestial irradiance, I_0
# G_0n: normal irradiance at 0,n 
# w1: hour angle for hourly endpoints (beginning)
# w2: hour angle for hourly endpoints (end)
# phi: latitude
# delta: declination at the day
def extr_irrad(G_0n, w1, w2, phi, delta):
	a = 12 * 3600 / math.pi
	b = math.pi / 180
	c = b * (w2-w1) * math.sin(phi) * math.sin(delta)
	d = math.cos(phi) * math.cos(delta) * (math.sin(w2)-math.sin(w1))
	return a * G_0n * (c + d)

def clearness_index(G_0n, G_n):
	return G_n / G_0n

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
def data_parse(datasets): 
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
				month_name = MONTH_TO_NUMBER[month["month"]]
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
	print("Optimal average monthly energy per square meter of PV: " + str(optimal_value) + " kWh/m^2")
	print("\n")

def main():
	print("\n")
	

	datasets = load_data()

	months_averaged_by_angle = data_parse(datasets)

	calculate_optimal_angle(months_averaged_by_angle)

if __name__ == "__main__":
	main()