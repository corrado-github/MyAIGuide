import pandas as pd
import csv


def retrieve_mentalstate_participant1(fname, data):
    """ Function updates a dataframe with mental state data for Participant 1

	fname: path to datafolder for participant 1
	data: pandas dataframe to store data
    """
	
  Year = ""
  Month = ""
  Day = ""
  with open(filename, newline="") as csvfile:
      csv_reader = csv.reader(csvfile)
      line_count = 0
      for i in csv_reader:
          line_count = line_count + 1
          if line_count > 1 and len(i):
              if len(i[0]):
                  Year = i[0]
              if len(i[1]):
                  Month = i[1]
                  if len(Month) == 1:
                      Month = "0" + Month
              if len(i[2]):
                  Day = i[2]
                  if len(Day) == 1:
                      Day = "0" + Day
              date = Year + "-" + Month + "-" + Day

              dict = {
                  "Really Good": "reallyGood",
		  "Good": "good",
		  "Fine": "fine",
                  "Variable but mostly good": "variableButMostlyGood",
		  "Ok, but also not really that great": "okButAlsoNotReallyThatGreat",
                  "Variable but mostly not great": "variableButMostlyNotGreat",
                  "Tired": "tired",
		  "Depressed": "depressed",  
              }
              if i[3] in dict:
                  data.loc[date, dict[i[3]]] = 1

    return data
