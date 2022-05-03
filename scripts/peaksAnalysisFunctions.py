import sys
sys.path.insert(1, '../src/MyAIGuide/utilities')

import pickle
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from dataFrameUtilities import check_if_zero_then_adjust_var_and_place_in_data, insert_data_to_tracker_mean_steps, subset_period, transformPain, predict_values, rollingMinMaxScalerMeanShift

plotWithScaling = False
plotMedianGraph = True

def addMinAndMax(data, regionName, plotFig, minProminenceForPeakDetect, windowForLocalPeakMinMaxFind):
  
  scoreBasedOnAmplitude = False
  debugMode = False
  debugModeGeneral = False
  
  # Finding local min and max of pain and removing subsquent min/max not separated by respectively max/min
  pain = np.array(data[regionName+'_RollingMean_MinMaxScaler'].tolist())
  maxpeaks, properties = find_peaks(pain, prominence=minProminenceForPeakDetect, width=windowForLocalPeakMinMaxFind)
  minpeaks, properties = find_peaks(-pain, prominence=minProminenceForPeakDetect, width=windowForLocalPeakMinMaxFind)
  if True:
    if plotFig:
      print("Before double max peaks removal: len(maxpeaks):", len(maxpeaks))
      print("Before double min peaks removal: len(minpeaks):", len(minpeaks))
    # Removing "double max peaks"
    lastSeenWasMaxPeak = False
    for i in range(0, len(data)):
      if i in maxpeaks:
        if lastSeenWasMaxPeak:
          maxpeaks = maxpeaks[maxpeaks != i]
        lastSeenWasMaxPeak = True
      if i in minpeaks:
        lastSeenWasMaxPeak = False
    # Removing "double min peaks"
    lastSeenWasMinPeak = False
    for i in range(0, len(data)):
      if i in minpeaks:
        if lastSeenWasMinPeak:
          minpeaks = minpeaks[minpeaks != i]
        lastSeenWasMinPeak = True
      if i in maxpeaks:
        lastSeenWasMinPeak = False
    if plotFig:
      print("After double max peaks removal: len(maxpeaks):", len(maxpeaks))
      print("After double min peaks removal: len(minpeaks):", len(minpeaks))
  
  # Storing in memory the sequence of mins and max
  painMinMaxSequence = []
  isMinOrMaxSequence = []
  for i in range(0, len(data)):
      if i in maxpeaks:
        painMinMaxSequence.append(i)
        isMinOrMaxSequence.append(True)
      if i in minpeaks:
        painMinMaxSequence.append(i)
        isMinOrMaxSequence.append(False)
  
  # Adding two columns in dataframe equal to pain values at min/max frame and to nan elsewhere
  data['max'] = float('nan')
  data['max'][maxpeaks] = data[regionName+'_RollingMean_MinMaxScaler'][maxpeaks].tolist()
  data['min'] = float('nan')
  data['min'][minpeaks] = data[regionName+'_RollingMean_MinMaxScaler'][minpeaks].tolist()
  
  # Finding strain min/max
  strain = np.array(data['regionSpecificstrain_RollingMean_MinMaxScaler'].tolist())
  maxpeaksstrain, properties = find_peaks(strain, prominence=minProminenceForPeakDetect, width=windowForLocalPeakMinMaxFind)
  minpeaksstrain, properties = find_peaks(-strain, prominence=minProminenceForPeakDetect, width=windowForLocalPeakMinMaxFind)
  data['maxstrain'] = float('nan')
  
  # Calculates for each strain peak the relative location in the min/max pain cycle
  negativeValue = 0
  positiveValue = 0
  # -1 : maxstrain slightly above maxPain
  # 0  : maxstrain at minPain
  # 1  : maxstrain slightly below maxPain
  maxstrainScores  = np.array([float('nan') for i in range(0, len(maxpeaksstrain))])
  maxstrainScores2 = np.array([float('nan') for i in range(0, len(maxpeaksstrain))])
  for ind, maxstrain in enumerate(maxpeaksstrain):
    indSequencePain = 0
    while indSequencePain + 1 < len(painMinMaxSequence) and not(painMinMaxSequence[indSequencePain] <= maxstrain and maxstrain <= painMinMaxSequence[indSequencePain + 1]):
      indSequencePain = indSequencePain + 1
    if indSequencePain + 1 < len(painMinMaxSequence) and painMinMaxSequence[indSequencePain] <= maxstrain and maxstrain <= painMinMaxSequence[indSequencePain + 1]:
      closestMaxPain = painMinMaxSequence[indSequencePain]   if isMinOrMaxSequence[indSequencePain] else painMinMaxSequence[indSequencePain+1]
      closestMinPain = painMinMaxSequence[indSequencePain+1] if isMinOrMaxSequence[indSequencePain] else painMinMaxSequence[indSequencePain]
      keepMaxPeakstrain = False
      if maxstrain >= closestMaxPain: # maxstrain >= closestMaxPain
        minPainCandidates = np.array([minPain for minPain in minpeaks if minPain >= closestMaxPain and maxstrain <= minPain])
        if len(minPainCandidates):
          keepMaxPeakstrain = True
          closestMinPain = minPainCandidates[0]
          # closestMaxPain <= maxstrain <= closestMinPain
          maxstrainScores[ind] = (maxstrain - closestMinPain) / (closestMinPain - closestMaxPain) # Negative value
          maxstrainScores2[ind] = pain[maxstrain+1] - pain[maxstrain] if maxstrain + 1 < len(pain) else 0
          print("strain peak relative location (Negative):", maxstrainScores[ind], "; Time:", data.index[maxstrain])
          negativeValue += 1
      else: # maxstrain < closestMaxPain
        minPainCandidates = np.array([minPain for minPain in minpeaks if minPain <= closestMaxPain and minPain <= maxstrain])
        if len(minPainCandidates):
          keepMaxPeakstrain = True
          closestMinPain = minPainCandidates[-1:][0]
          # closestMinPain <= maxstrain <= closestMaxPain
          maxstrainScores[ind] = (maxstrain - closestMinPain) / (closestMaxPain - closestMinPain) # Positive value
          maxstrainScores2[ind] = pain[maxstrain+1] - pain[maxstrain] if maxstrain + 1 < len(pain) else 0
          print("strain peak relative location (Positive):", maxstrainScores[ind], "; Time:", data.index[maxstrain])
          positiveValue += 1
      if keepMaxPeakstrain:
        if True:
          # if True:
            # minstrainCandidates = np.array([minstrainPeak for minstrainPeak in minpeaksstrain if minstrainPeak <= maxstrain])
            # minstrainPeak = minstrainCandidates[-1] if len(minstrainCandidates) else 0 # "else 0" needs to be improved
          data['maxstrain'][maxstrain - 1] = 0
          data['maxstrain'][maxstrain]     = data['regionSpecificstrain_RollingMean_MinMaxScaler'][maxstrain] # strain[maxstrain] - strain[minstrainPeak]
          data['maxstrain'][maxstrain + 1] = 0     
        else:
          data['maxstrain'][maxstrain - 1] = 0.5
          data['maxstrain'][maxstrain]     = 0.5 + maxstrainScores[ind]/2
          data['maxstrain'][maxstrain + 1] = 0.5
  
  if debugModeGeneral: print("negativeValue:", negativeValue)
  if debugModeGeneral: print("positiveValue:", positiveValue)
  
  # Calculating total number of days where the pain is respectively ascending and descending
  minPeak = minpeaks[0] if len(minpeaks) else 0
  totDaysAscendingPain  = 0
  totDaysDescendingPain = 0
  toAddAscending  = []
  toAddDescending = []
  for maxPeak in maxpeaks:
    if minPeak < maxPeak:
      toAddAscending.append(maxPeak - minPeak)
      # totDaysAscendingPain += maxPeak - minPeak
      if debugMode: print("should be positive 1: ", maxPeak - minPeak)
    minPeakCandidates = np.array([minPain for minPain in minpeaks if minPain >= maxPeak])
    if len(minPeakCandidates):
      minPeak = minPeakCandidates[0]
      toAddDescending.append(minPeak - maxPeak)
      # totDaysDescendingPain += minPeak - maxPeak
      if debugMode: print("should be positive 2: ", minPeak - maxPeak)
    else:
      minPeak = -1
  totDaysAscendingPain = np.sum(np.array(toAddAscending[1:-1]))
  totDaysDescendingPain = np.sum(np.array(toAddDescending[1:-1]))
  if debugModeGeneral: print("totDaysAscendingPain:", totDaysAscendingPain)
  if debugModeGeneral: print("totDaysDescendingPain:", totDaysDescendingPain)
  
  # Plotting for each strain peak the relative location in the min/max pain cycle
  if plotFig:
    fig2, axes = plt.subplots(nrows=1, ncols=1)
    sns.stripplot(y="col1", data=pd.DataFrame(data={'col1': maxstrainScores}), size=4, color=".3", linewidth=0)
    plt.show()
    fig2, axes = plt.subplots(nrows=1, ncols=1)
    plt.hist(maxstrainScores)
    plt.show()
  
  # strain peaks amplitudes vs Pain peaks amplitudes: calculating values
  painMinMaxAmplitudes   = []
  strainMinMaxAmplitudes = []
  if True:
    minMaxTimeTolerance    = 7
    analyzestrainResponseAfter = False
    for maxPainPeak in maxpeaks:
      minPainCandidates = np.array([minPainPeak for minPainPeak in minpeaks if minPainPeak <= maxPainPeak])
      if len(minPainCandidates):
        minPainPeak = minPainCandidates[-1]
        correspondingstrainPeakCandidates = [maxstrain for maxstrain in maxpeaksstrain if maxstrain >= minPainPeak - minMaxTimeTolerance and maxstrain <= maxPainPeak + minMaxTimeTolerance]
        if len(correspondingstrainPeakCandidates):
          maxstrainPeak = correspondingstrainPeakCandidates[np.argmax([strain[maxstrain] for maxstrain in correspondingstrainPeakCandidates])]
          minstrainCandidates = np.array([minstrainPeak for minstrainPeak in minpeaksstrain if minstrainPeak <= maxstrainPeak]) if not(analyzestrainResponseAfter) else np.array([minstrainPeak for minstrainPeak in minpeaksstrain if minstrainPeak >= maxstrainPeak])
          if len(minstrainCandidates):
            minstrainPeak = minstrainCandidates[-1] if not(analyzestrainResponseAfter) else minstrainCandidates[0]
            painMinMaxAmplitudes.append(pain[maxPainPeak] - pain[minPainPeak])
            strainMinMaxAmplitudes.append(strain[maxstrainPeak] - strain[minstrainPeak])
            if plotFig:
              print("date: ", data.index[maxPainPeak], "; pain: ", pain[maxPainPeak] - pain[minPainPeak], "; strain: ", strain[maxstrainPeak] - strain[minstrainPeak])
        else: # THIS ELSE MIGHT NEED TO BE REMOVED
          painMinMaxAmplitudes.append(pain[maxPainPeak] - pain[minPainPeak])
          strainMinMaxAmplitudes.append(0)
          if plotFig:
            print("date: ", data.index[maxPainPeak], "; pain: ", pain[maxPainPeak] - pain[minPainPeak], "; strain: ", 0)
  
  if plotFig:
    print("max:", [data.index[peak] for peak in maxpeaks])
    print("min:", [data.index[peak] for peak in minpeaks])
  
  return [maxstrainScores, totDaysAscendingPain, totDaysDescendingPain, minpeaks, maxpeaks, maxstrainScores2, strainMinMaxAmplitudes, painMinMaxAmplitudes, maxpeaksstrain]



def prepareForPlotting(data, region, minpeaks, maxpeaks):
  
  data['painAscending']  = data[region + '_RollingMean_MinMaxScaler']
  data['painDescending'] = data[region + '_RollingMean_MinMaxScaler']
  data['maxstrain2']     = data['maxstrain']
  
  allPeaks = np.concatenate((minpeaks, maxpeaks))
  ascending = True
  ascendingElement  = [0 for i in range(0, len(data))]
  descendingElement = [0 for i in range(0, len(data))]
  if len(allPeaks) and min(allPeaks) in maxpeaks:
    ascending = False
  if len(allPeaks):
    for i in range(min(allPeaks), max(allPeaks)):
      if i in maxpeaks:
        ascending = False
      if i in minpeaks:
        ascending = True
      if ascending:
        ascendingElement[i] = 1
      else:
        descendingElement[i] = 1
    
    data['painAscending'][[ind for ind, val in enumerate(descendingElement) if val or ind < min(allPeaks) or ind > max(allPeaks)]] = float('nan')
    data['painDescending'][[ind for ind, val in enumerate(ascendingElement) if val or ind < min(allPeaks) or ind > max(allPeaks)]] = float('nan')
    data['maxstrain2'][[ind for ind in range(0, len(data)) if ind < min(allPeaks) or ind > max(allPeaks)]] = float('nan')
    
    data = data.drop(columns=[region + '_RollingMean_MinMaxScaler', 'max', 'min', 'maxstrain', 'regionSpecificstrain_RollingMean_MinMaxScaler'])
  
  return data

def plottingOptions(axes, axesNum, text, legendsText, locLegend, sizeLegend):
  if legendsText:
    axes[axesNum].legend(legendsText, loc=locLegend, bbox_to_anchor=(1, 0.5))#, prop={'size': sizeLegend})
  else:
    if plotWithScaling:
      axes[axesNum].legend(loc=locLegend, prop={'size': sizeLegend})
    else:
      axes[axesNum].legend(loc=locLegend, bbox_to_anchor=(1, 0.5))#, prop={'size': sizeLegend})
  axes[axesNum].title.set_text(text)
  if plotWithScaling:
    axes[axesNum].title.set_fontsize(5)
  axes[axesNum].title.set_position([0.5, 0.93])
  axes[axesNum].get_xaxis().set_visible(False)

def visualizeRollingMinMaxScalerofRollingMeanOfstrainAndPain(data, region, list_of_stressors, strainor_coef, window, window2, rollingMedianWindow, minProminenceForPeakDetect, windowForLocalPeakMinMaxFind, plotGraph):
  
  if plotGraph:
    if plotMedianGraph:
      fig, axes = plt.subplots(nrows=6, ncols=1)
    else:
      fig, axes = plt.subplots(nrows=5, ncols=1)
  
  fig.subplots_adjust(left=0.02, bottom=0.05, right=0.90, top=0.97, wspace=None, hspace=0.25)
  
  scaler = MinMaxScaler()
  
  # Plotting potential stressors causing pain in region
  data[list_of_stressors] = scaler.fit_transform(data[list_of_stressors])
  if plotGraph:
    data[list_of_stressors].plot(ax=axes[0], linestyle='', marker='o', markersize=0.5)
    plottingOptions(axes, 0, 'stressors causing ' + region, [], 'upper right' if plotWithScaling else 'center left', 3 if plotWithScaling else 8)

  # Plotting strain and pain
  strain_and_pain = ["regionSpecificstrain", region]
  data["regionSpecificstrain"] = np.zeros(len(data[list_of_stressors[0]]))
  for idx, strainor in enumerate(list_of_stressors):
    data["regionSpecificstrain"] = data["regionSpecificstrain"] + strainor_coef[idx] * data[strainor]
  data[strain_and_pain] = scaler.fit_transform(data[strain_and_pain])
  if plotGraph:
    data[strain_and_pain].plot(ax=axes[1], linestyle='', marker='o', markersize=0.5)
    plottingOptions(axes, 1, 'strain (linear combination of previous stressors) and pain', ['strain', 'pain'], 'center left', 8)

  # Plotting Rolling Mean of strain and pain
  for var in strain_and_pain:
    data[var + "_RollingMean"] = data[var].rolling(window).mean()
  strain_and_pain_rollingMean = [name + "_RollingMean" for name in strain_and_pain]
  data[strain_and_pain_rollingMean] = scaler.fit_transform(data[strain_and_pain_rollingMean])
  if plotGraph:
    data[strain_and_pain_rollingMean].plot(ax=axes[2])
    plottingOptions(axes, 2, 'Rolling mean of strain and pain', ['strain', 'pain'], 'center left', 8)
  
  # Plotting Rolling MinMaxScaler of Rolling Mean of strain and pain
  strain_and_pain_RollingMean_MinMaxScaler = [name + "_MinMaxScaler" for name in strain_and_pain_rollingMean]
  if window2:
    for columnName in strain_and_pain_rollingMean:
      data[columnName + "_MinMaxScaler"] = rollingMinMaxScalerMeanShift(data, columnName, window2, window)
  else:
    for columnName in strain_and_pain_rollingMean:
      data[columnName + "_MinMaxScaler"] = data[columnName]
  if plotGraph:
    data[strain_and_pain_RollingMean_MinMaxScaler].plot(ax=axes[3])
    plottingOptions(axes, 3, 'Rolling MinMaxScaler of rolling mean of strain and pain', ['strain', 'pain'], 'center left', 8)

  # Peaks analysis
  data2 = data[strain_and_pain_RollingMean_MinMaxScaler].copy()
  data2 = data2.rolling(rollingMedianWindow).median()
  if plotMedianGraph:
    data2[strain_and_pain_RollingMean_MinMaxScaler].plot(ax=axes[4])
    plottingOptions(axes, 4, 'Rolling median of rolling MinMaxScaler of rolling mean of strain and pain', ['strain', 'pain'], 'center left', 8)
  [maxstrainScores, totDaysAscendingPain, totDaysDescendingPain, minpeaks, maxpeaks, maxstrainScores2, strainMinMaxAmplitudes, painMinMaxAmplitudes, maxpeaksstrain] = addMinAndMax(data2, region, False, minProminenceForPeakDetect, windowForLocalPeakMinMaxFind)
  data2 = prepareForPlotting(data2, region, minpeaks, maxpeaks)
  if plotGraph:
    if plotMedianGraph:
      data2.plot(ax=axes[5])
      plottingOptions(axes, 5, "Peaks Analysis", ['painAscending', 'painDescending', 'Peakstrain'], 'center left', 8)
      axes[5].get_xaxis().set_visible(True)
    else:
      data2.plot(ax=axes[4])
      plottingOptions(axes, 4, "Peaks Analysis", ['painAscending', 'painDescending', 'Peakstrain'], 'center left', 8)
      axes[4].get_xaxis().set_visible(True)
  
  nonNanLocations = np.argwhere(~np.isnan(maxstrainScores))
  nonNanLocations = nonNanLocations.flatten()

  maxpeaksstrain  = maxpeaksstrain[nonNanLocations]
  maxstrainScores = maxstrainScores[nonNanLocations]
  
  plt.xticks([data2.index[ind] for ind in maxpeaksstrain], [int(val*100)/100 for val in maxstrainScores], rotation='vertical')
  
  # Showing the final plot
  if plotGraph:
    plt.show()
  
  # Linear regression between strain and pain amplitudes
  if len(strainMinMaxAmplitudes):
    reg = LinearRegression().fit(np.array([strainMinMaxAmplitudes]).reshape(-1, 1), np.array([painMinMaxAmplitudes]).reshape(-1, 1))
    if plotGraph:
      print("regression score:", reg.score(np.array([strainMinMaxAmplitudes]).reshape(-1, 1), np.array([painMinMaxAmplitudes]).reshape(-1, 1)))
    pred = reg.predict(np.array([i for i in range(0, 10)]).reshape(-1, 1))
    if plotGraph:
      fig3, axes = plt.subplots(nrows=1, ncols=1)
      plt.plot(strainMinMaxAmplitudes, painMinMaxAmplitudes, '.')
      plt.plot([i for i in range(0, 10)], pred)
      plt.xlim([0, 1])
      plt.ylim([0, 1])
      plt.show()
  
  return [maxstrainScores, maxstrainScores2, totDaysAscendingPain, totDaysDescendingPain, data, data2, strainMinMaxAmplitudes, painMinMaxAmplitudes]


def calculateForAllRegions(data, parameters, plotGraphs, saveData):

  rollingMeanWindow = parameters['rollingMeanWindow']
  rollingMinMaxScalerWindow = parameters['rollingMinMaxScalerWindow']
  rollingMedianWindow = parameters['rollingMedianWindow']
  minProminenceForPeakDetect = parameters['minProminenceForPeakDetect']
  windowForLocalPeakMinMaxFind = parameters['windowForLocalPeakMinMaxFind']
  plotGraph = parameters['plotGraph']
  allBodyRegionsArmIncluded = parameters['allBodyRegionsArmIncluded']
  
  data = data.rename(columns={'tracker_mean_distance': 'distance', 'tracker_mean_denivelation': 'denivelation', 'manicTimeDelta_corrected': 'timeOnComputer', 'whatPulseT_corrected': 'mouseAndKeyboardPressNb'})
  
  # Knee plots
  [maxstrainScoresKnee, maxstrainScores2Knee, totDaysAscendingPainKnee, totDaysDescendingPainKnee, dataKnee, data2Knee, strainMinMaxAmplitudesKnee, painMinMaxAmplitudesKnee] = visualizeRollingMinMaxScalerofRollingMeanOfstrainAndPain(data, "kneePain", ["distance", "denivelation", "timeDrivingCar", "swimmingKm", "cycling"], [1, 1, 0.15, 1, 0.5], rollingMeanWindow, rollingMinMaxScalerWindow, rollingMedianWindow, minProminenceForPeakDetect, windowForLocalPeakMinMaxFind, plotGraph)

  # Finger hand arm plots
  if allBodyRegionsArmIncluded:
    [maxstrainScoresArm, maxstrainScores2Arm, totDaysAscendingPainArm, totDaysDescendingPainArm, dataArm, data2Arm, strainMinMaxAmplitudesArm, painMinMaxAmplitudesArm] = visualizeRollingMinMaxScalerofRollingMeanOfstrainAndPain(data, "fingerHandArmPain", ["whatPulseT_corrected", "climbingDenivelation", "climbingMaxEffortIntensity", "climbingMeanEffortIntensity", "swimmingKm", "surfing", "viaFerrata", "scooterRiding"], [1, 0.25, 0.5, 0.25, 0.7, 0.9, 0.8, 0.9], rollingMeanWindow, rollingMinMaxScalerWindow, rollingMedianWindow, minProminenceForPeakDetect, windowForLocalPeakMinMaxFind, plotGraph)

  # Forehead eyes plots
  [maxstrainScoresHead, maxstrainScores2Head, totDaysAscendingPainHead, totDaysDescendingPainHead, dataHead, data2Head, strainMinMaxAmplitudesHead, painMinMaxAmplitudesHead] = visualizeRollingMinMaxScalerofRollingMeanOfstrainAndPain(data, "foreheadEyesPain", ["timeOnComputer", "timeDrivingCar"], [1, 0.8], rollingMeanWindow, rollingMinMaxScalerWindow, rollingMedianWindow, minProminenceForPeakDetect, windowForLocalPeakMinMaxFind, plotGraph)

  # All regions together
  if allBodyRegionsArmIncluded:
    maxstrainScores = np.concatenate((np.concatenate((maxstrainScoresKnee, maxstrainScoresArm)), maxstrainScoresHead))
    strainMinMaxAmplitudes = np.concatenate((np.concatenate((strainMinMaxAmplitudesKnee, strainMinMaxAmplitudesArm)), strainMinMaxAmplitudesHead))
    painMinMaxAmplitudes   = np.concatenate((np.concatenate((painMinMaxAmplitudesKnee, painMinMaxAmplitudesArm)), painMinMaxAmplitudesHead))
    if plotGraphs:
      plt.hist(maxstrainScores)
      plt.show()
  else:
    # fig, axes = plt.subplots(nrows=2, ncols=1)
    maxstrainScores = np.concatenate((maxstrainScoresKnee, maxstrainScoresHead))
    strainMinMaxAmplitudes = np.concatenate((strainMinMaxAmplitudesKnee, strainMinMaxAmplitudesHead))
    painMinMaxAmplitudes   = np.concatenate((painMinMaxAmplitudesKnee, painMinMaxAmplitudesHead))
    if plotGraphs:
      plt.hist(maxstrainScores)
      plt.show()
      
  regScore = 0
  if True:
    reg = LinearRegression().fit(np.array([strainMinMaxAmplitudes]).reshape(-1, 1), np.array([painMinMaxAmplitudes]).reshape(-1, 1))
    regScore = reg.score(np.array([strainMinMaxAmplitudes]).reshape(-1, 1), np.array([painMinMaxAmplitudes]).reshape(-1, 1))
    if plotGraphs:
      print("regression score:", regScore)
      pred = reg.predict(np.array([i for i in range(0, 10)]).reshape(-1, 1))
      fig3, axes = plt.subplots(nrows=1, ncols=1)
      plt.plot(strainMinMaxAmplitudes, painMinMaxAmplitudes, '.')
      plt.plot([i for i in range(0, 10)], pred)
      plt.xlabel('Strain Peak Amplitude')
      plt.ylabel('Pain Peak Amplitude')
      plt.xlim([0, 1])
      plt.ylim([0, 1])
      plt.show()
  
  # Saving data
  if saveData:
    output = open("peaksData.txt", "wb")
    if allBodyRegionsArmIncluded:
      pickle.dump({'Knee': [maxstrainScoresKnee, totDaysAscendingPainKnee, totDaysDescendingPainKnee, dataKnee, data2Knee, strainMinMaxAmplitudesKnee, painMinMaxAmplitudesKnee], 'Arm': [maxstrainScoresArm, totDaysAscendingPainArm, totDaysDescendingPainArm, dataArm, data2Arm, strainMinMaxAmplitudesArm, painMinMaxAmplitudesArm], 'Head': [maxstrainScoresHead, totDaysAscendingPainHead, totDaysDescendingPainHead, dataHead, data2Head, strainMinMaxAmplitudesHead, painMinMaxAmplitudesHead]}, output)
    else:
      pickle.dump({'Knee': [maxstrainScoresKnee, totDaysAscendingPainKnee, totDaysDescendingPainKnee, dataKnee, data2Knee, strainMinMaxAmplitudesKnee, painMinMaxAmplitudesKnee], 'Head': [maxstrainScoresHead, totDaysAscendingPainHead, totDaysDescendingPainHead, dataHead, data2Head, strainMinMaxAmplitudesHead, painMinMaxAmplitudesHead]}, output)
    output.close()
  
  nbAscendingDays  = totDaysAscendingPainKnee + totDaysAscendingPainHead
  nbDescendingDays = totDaysDescendingPainKnee + totDaysDescendingPainHead
  
  extendingAscendingNbDays  = nbAscendingDays + 0.2 * nbDescendingDays
  extendingDescendingNbDays = 0.8 * nbDescendingDays
  
  nbPointsInAscendingDays  = np.sum(np.logical_or(maxstrainScores >= 0, maxstrainScores <= -0.8))
  nbPointsInDescendingDays = np.sum(np.logical_and(maxstrainScores <= 0, maxstrainScores >= -0.8))
  
  if False:
    print("nbPointsInAscendingDays:", nbPointsInAscendingDays, "; nbPointsInDescendingDays:", nbPointsInDescendingDays)
    print("extendingAscendingNbDays:", extendingAscendingNbDays, "; extendingDescendingNbDays:", extendingDescendingNbDays)
    print("rapport: ", (nbPointsInAscendingDays / extendingAscendingNbDays) / (nbPointsInDescendingDays / extendingDescendingNbDays))
  
  return [(nbPointsInAscendingDays / extendingAscendingNbDays) / (nbPointsInDescendingDays / extendingDescendingNbDays), nbAscendingDays + nbDescendingDays, regScore, nbAscendingDays, nbDescendingDays]


def calculateForAllRegionsParticipant2(data, parameters, plotGraphs, saveData=False):

  rollingMeanWindow = parameters['rollingMeanWindow']
  rollingMinMaxScalerWindow = parameters['rollingMinMaxScalerWindow']
  rollingMedianWindow = parameters['rollingMedianWindow']
  minProminenceForPeakDetect = parameters['minProminenceForPeakDetect']
  windowForLocalPeakMinMaxFind = parameters['windowForLocalPeakMinMaxFind']
  plotGraph = parameters['plotGraph']

  # Knee plots
  [maxstrainScoresKnee, maxstrainScores2Knee, totDaysAscendingPainKnee, totDaysDescendingPainKnee, dataKnee, data2Knee, strainMinMaxAmplitudes, painMinMaxAmplitudes] = visualizeRollingMinMaxScalerofRollingMeanOfstrainAndPain(data, "kneepain", ["steps", "denivelation"], [1, 1], rollingMeanWindow, rollingMinMaxScalerWindow, rollingMedianWindow, minProminenceForPeakDetect, windowForLocalPeakMinMaxFind, plotGraph)

  maxstrainScores = maxstrainScoresKnee
  if plotGraphs:
    plt.hist(maxstrainScores)
    plt.show()

  # Saving data
  if saveData:
    output = open("peaksData.txt", "wb")
    pickle.dump({'Knee': [maxstrainScoresKnee, totDaysAscendingPainKnee, totDaysDescendingPainKnee, dataKnee, data2Knee]}, output)
    output.close()
  
  nbAscendingDays  = totDaysAscendingPainKnee
  nbDescendingDays = totDaysDescendingPainKnee
  
  extendingAscendingNbDays  = nbAscendingDays + 0.2 * nbDescendingDays
  extendingDescendingNbDays = 0.8 * nbDescendingDays
  
  nbPointsInAscendingDays  = np.sum(np.logical_or(maxstrainScores >= 0, maxstrainScores <= -0.8))
  nbPointsInDescendingDays = np.sum(np.logical_and(maxstrainScores <= 0, maxstrainScores >= -0.8))
  
  if False:
    print("nbPointsInAscendingDays:", nbPointsInAscendingDays, "; nbPointsInDescendingDays:", nbPointsInDescendingDays)
    print("extendingAscendingNbDays:", extendingAscendingNbDays, "; extendingDescendingNbDays:", extendingDescendingNbDays)
    print("rapport: ", (nbPointsInAscendingDays / extendingAscendingNbDays) / (nbPointsInDescendingDays / extendingDescendingNbDays))
  
  return [(nbPointsInAscendingDays / extendingAscendingNbDays) / (nbPointsInDescendingDays / extendingDescendingNbDays), nbAscendingDays + nbDescendingDays]


def calculateForAllRegionsParticipant8(data, parameters, plotGraphs, saveData=False):

  rollingMeanWindow = parameters['rollingMeanWindow']
  rollingMinMaxScalerWindow = parameters['rollingMinMaxScalerWindow']
  rollingMedianWindow = parameters['rollingMedianWindow']
  minProminenceForPeakDetect = parameters['minProminenceForPeakDetect']
  windowForLocalPeakMinMaxFind = parameters['windowForLocalPeakMinMaxFind']
  plotGraph = parameters['plotGraph']

  # Knee plots
  [maxstrainScoresKnee, maxstrainScores2Knee, totDaysAscendingPainKnee, totDaysDescendingPainKnee, dataKnee, data2Knee, strainMinMaxAmplitudes, painMinMaxAmplitudes] = visualizeRollingMinMaxScalerofRollingMeanOfstrainAndPain(data, "kneepain", ["steps"], [1], rollingMeanWindow, rollingMinMaxScalerWindow, rollingMedianWindow, minProminenceForPeakDetect, windowForLocalPeakMinMaxFind, plotGraph)

  maxstrainScores = maxstrainScoresKnee
  if plotGraphs:
    plt.hist(maxstrainScores, range=(-1, 1))
    plt.show()

  # Saving data
  if saveData:
    output = open("peaksData.txt", "wb")
    pickle.dump({'Knee': [maxstrainScoresKnee, totDaysAscendingPainKnee, totDaysDescendingPainKnee, dataKnee, data2Knee]}, output)
    output.close()
  
  nbAscendingDays  = totDaysAscendingPainKnee
  nbDescendingDays = totDaysDescendingPainKnee
  
  extendingAscendingNbDays  = nbAscendingDays + 0.2 * nbDescendingDays
  extendingDescendingNbDays = 0.8 * nbDescendingDays
  
  nbPointsInAscendingDays  = np.sum(np.logical_or(maxstrainScores >= 0, maxstrainScores <= -0.8))
  nbPointsInDescendingDays = np.sum(np.logical_and(maxstrainScores <= 0, maxstrainScores >= -0.8))
  
  if False:
    print("nbPointsInAscendingDays:", nbPointsInAscendingDays, "; nbPointsInDescendingDays:", nbPointsInDescendingDays)
    print("extendingAscendingNbDays:", extendingAscendingNbDays, "; extendingDescendingNbDays:", extendingDescendingNbDays)
    print("rapport: ", (nbPointsInAscendingDays / extendingAscendingNbDays) / (nbPointsInDescendingDays / extendingDescendingNbDays))
  
  return [(nbPointsInAscendingDays / extendingAscendingNbDays) / (nbPointsInDescendingDays / extendingDescendingNbDays), nbAscendingDays + nbDescendingDays]


def calculateForAllRegionsParticipant3_4_5_6_7_9(data, parameters, plotGraphs, stressorName, painRegionName, saveData=False):

  rollingMeanWindow = parameters['rollingMeanWindow']
  rollingMinMaxScalerWindow = parameters['rollingMinMaxScalerWindow']
  rollingMedianWindow = parameters['rollingMedianWindow']
  minProminenceForPeakDetect = parameters['minProminenceForPeakDetect']
  windowForLocalPeakMinMaxFind = parameters['windowForLocalPeakMinMaxFind']
  plotGraph = parameters['plotGraph']

  # Knee plots
  [maxstrainScoresKnee, maxstrainScores2Knee, totDaysAscendingPainKnee, totDaysDescendingPainKnee, dataKnee, data2Knee, strainMinMaxAmplitudes, painMinMaxAmplitudes] = visualizeRollingMinMaxScalerofRollingMeanOfstrainAndPain(data, painRegionName, [stressorName], [1], rollingMeanWindow, rollingMinMaxScalerWindow, rollingMedianWindow, minProminenceForPeakDetect, windowForLocalPeakMinMaxFind, plotGraph)

  maxstrainScores = maxstrainScoresKnee
  if plotGraphs:
    plt.hist(maxstrainScores, range=(-1, 1))
    plt.show()

  # Saving data
  if saveData:
    output = open("peaksData.txt", "wb")
    pickle.dump({'Knee': [maxstrainScoresKnee, totDaysAscendingPainKnee, totDaysDescendingPainKnee, dataKnee, data2Knee]}, output)
    output.close()
  
  nbAscendingDays  = totDaysAscendingPainKnee
  nbDescendingDays = totDaysDescendingPainKnee
  
  extendingAscendingNbDays  = nbAscendingDays + 0.2 * nbDescendingDays
  extendingDescendingNbDays = 0.8 * nbDescendingDays
  
  nbPointsInAscendingDays  = np.sum(np.logical_or(maxstrainScores >= 0, maxstrainScores <= -0.8))
  nbPointsInDescendingDays = np.sum(np.logical_and(maxstrainScores <= 0, maxstrainScores >= -0.8))
  
  if False:
    print("nbPointsInAscendingDays:", nbPointsInAscendingDays, "; nbPointsInDescendingDays:", nbPointsInDescendingDays)
    print("extendingAscendingNbDays:", extendingAscendingNbDays, "; extendingDescendingNbDays:", extendingDescendingNbDays)
    print("rapport: ", (nbPointsInAscendingDays / extendingAscendingNbDays) / (nbPointsInDescendingDays / extendingDescendingNbDays))
  
  return [(nbPointsInAscendingDays / extendingAscendingNbDays) / (nbPointsInDescendingDays / extendingDescendingNbDays), nbAscendingDays + nbDescendingDays]
