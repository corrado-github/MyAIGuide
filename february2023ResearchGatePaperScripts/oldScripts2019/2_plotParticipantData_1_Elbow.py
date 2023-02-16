# This scripts assumes that the dataframe has been created and saved in data.txt

import pickle

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dataFrameUtilities import addRollingMeanColumns, selectColumns, selectTime
from sklearn.preprocessing import MinMaxScaler

input = open("../data/preprocessed/preprocessedDataParticipant1.txt", "rb")
data = pickle.load(input)
input.close()

timeSelected = selectTime(data, "2016-01-15", "2019-03-06")

pain = selectColumns(timeSelected, ["forearmElbowPain"])
pain = addRollingMeanColumns(pain, ["forearmElbowPain"], 21)

timeSelected["swimAndSurf"] = timeSelected["swimming"] + timeSelected["surfing"]
timeSelected["climbs"] = timeSelected["climbing"] + timeSelected["viaFerrata"]

env = addRollingMeanColumns(timeSelected, ["whatPulseT", "swimAndSurf", "climbs"], 21)

envOrdi = env[["whatPulseT"]]
envSport = env[["swimAndSurf", "climbs"]]
envSportMean = env[["whatPulseTRollingMean", "swimAndSurfRollingMean", "climbsRollingMean"]]

fig, axes = plt.subplots(nrows=4, ncols=1)

pain.plot(ax=axes[0])
envOrdi.plot(ax=axes[1])
envSport.plot(ax=axes[2])
envSportMean.plot(ax=axes[3])

leg = plt.legend(loc="best")
leg.set_draggable(True)

plt.show()
