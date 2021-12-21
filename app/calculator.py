import json
import datetime
from pathlib import Path
import math
import requests


class Calculator:
    def __init__(self):
        """
        location_api_url: api url to retrieve location for particular postcode
        weather_api_url: api url to retrieve weather details at specific location, with all details for hourly weather
        history including uvIndex, cloud cover, etc.
        public_holiday_api_url: api url to retrieve list of public holiday across states Australia including date, name
        and jurisdiction.
        """
        self.location_api_url = "http://118.138.246.158/api/v1/location?postcode="
        self.weather_api_url = "http://118.138.246.158/api/v1/weather?location="
        self.public_holiday_api_url = "https://data.gov.au/data/api/3/action/datastore_search?resource_id=33673aca-0857-42e5-b8f0-9981b4755686"

    def get_charging_cost(self, initial_state, final_state, capacity, charger_configuration, start_time, start_date, post_code, suburb):
        """
        get_charging_cost method used to determine the cost of charging given the inputs entered on the html page
        :param initial_state: the initial state of charge of the car battery (int)
        :param final_state: the final state of charge of the car battery (int)
        :param capacity: the capacity of the car battery in kWh (int)
        :param charger_configuration: the option of charger configuration that users would like to choose when they
         start charge their vehicle (int)
        :param start_time: the time at which charging will begin (string)
        :param start_date: the date that the charging will begin (string)
        :param post_code: the post code of the area where charging will occur (string)
        :param suburb: the suburb that user wants to retrieve details
        of the area where charging will occur because one postcode can return multiple suburb (string)
        """
        # Begin by converting arguments to appropriate type as they are passed in as strings, also determine power and
        # cost based off charger configuration selected
        initial_state = int(initial_state)
        final_state = int(final_state)
        capacity = int(capacity)
        post_code = int(post_code)
        power, cost = self.get_power(int(charger_configuration))

        # Retrieve total cost of charging (REQ1) before any savings are added
        total_cost = self.cost_calculation(initial_state, final_state, capacity, power, cost, start_time, start_date, post_code)

        # Determine amount of money generated from solar panels with respect to the cloud coverage and sun hours whilst
        # charging
        money_saved_from_solar_energy_generated = self.calculate_solar_energy_savings_from_any_date(initial_state, final_state, capacity, power, cost, start_time, start_date, post_code, suburb)
        # This function can return a -1 if either of the API calls it makes fails (i.e. from an invalid postcode or
        # the solar data cannot be retrieved).
        if money_saved_from_solar_energy_generated == -1:
            return -1

        final_cost = total_cost - money_saved_from_solar_energy_generated

        # If the savings generated is more than the total cost to charge, the user is not charged anything, display a
        # message with this info such that "$0.00" does not look like an incorrect answer
        if money_saved_from_solar_energy_generated >= total_cost:
            return "$0.00 as energy received from solar panels was greater than energy consumed!"
        # If the resulting value is more than a dollar only show up to two decimals places for the cents
        elif final_cost > 1:
            return "$" + str(round(final_cost, 2))
        # If the resulting value is less than a dollar, give slightly more accurate information to the user (i.e., 4
        # decimal places)
        return "$" + str(round(final_cost, 4))

    def get_charging_time(self, initial_state, final_state, capacity, charger_configuration):
        """
        get_charging_time method used to determine the total time charging given the inputs entered on the html page
        :param initial_state: the initial state of charge of the car battery (int)
        :param final_state: the final state of charge of the car battery (int)
        :param capacity: the capacity of the car battery in kWh (int)
        :param charger_configuration: the option of charger configuration that users would like to choose when they
         start charge their vehicle (int)
        """
        power, cost = self.get_power(int(charger_configuration))
        time = self.time_calculation(initial_state, final_state, capacity, power)
        return self.format_time(time)

    def get_power(self, charger_configuration):
        """
        get_power method used to decide which power will be used to charge the vehicle based on charger_configuration
        input from html page
        :param charger_configuration: the option of charger configuration that users would like to choose when they
         start charge their vehicle (int)
        """
        if charger_configuration == 1:
            return 2, 5
        elif charger_configuration == 2:
            return 3.6, 7.5
        elif charger_configuration == 3:
            return 7.2, 10
        elif charger_configuration == 4:
            return 11, 12.5
        elif charger_configuration == 5:
            return 22, 15
        elif charger_configuration == 6:
            return 36, 20
        elif charger_configuration == 7:
            return 90, 30
        else:
            return 350, 50

    def cost_calculation(self, initial_state, final_state, capacity, power, cost, start_time, start_date, post_code):
        """
        cost_calculation method used to determine the total cost of charging given the inputs entered on the html page
        :param initial_state: the initial state of charge of the car battery (int)
        :param final_state: the final state of charge of the car battery (int)
        :param capacity: the capacity of the car battery in kWh (int)
        :param power: the power supplied to the car battery via the charging outlet in kW (int)
        :param start_time: the time at which charging will begin (string)
        :param start_date: the date that the charging will begin (string)
        :param post_code: the post code of the area where charging will occur (string)
        :return: the total cost to charge the car's battery from its initial state of charge to the required (final)
        state of charge as per the arguments.
        """
        count = 0   # Setting up count used to determine the number of minutes processed in the calculation
        final_cost = 0  # Represents the cost to charge

        # Determining how long it takes to charge as per the parameters
        time = self.time_calculation(initial_state, final_state, capacity, power)
        time_required = int(time)

        base_price = cost
        cost = base_price / (time_required + 1) / 100   # Converting cost to be dollars per minute of charging
        cost_val = cost

        # Determining the minute of the day that charging will begin (i.e., a number in the range 1 - 1400)
        current_minute = self.get_minute_from_start_time(start_time)
        date = start_date

        surcharge_factor = self.get_date_surcharge(date, post_code)

        # Ensuring post_code is valid australian post code: get_date_surcharge() returns -1 if not
        if surcharge_factor == -1:
            return -1

        # Calculate the cost to charge for each minute that is required as calculated above
        while count <= time_required:
            # If the current minute is 1440, the end of the current day has been reached, get the next date and
            # determine surcharge factor of new date
            if current_minute == 1440:
                date = self.get_next_date(date)
                current_minute = 1  # Resetting current minute back to 1 as it is the first minute of the next day
                surcharge_factor = self.get_date_surcharge(date, post_code)

            # Checking if the current minute is in peak time and setting base_price accordingly
            if not self.is_peak(current_minute):
                is_current_minute_peak = False
                cost_val = cost/2
            else:
                is_current_minute_peak = True

            # Performing the cost calculation for the current minute of charging
            price = ((final_state - initial_state) / 100) * capacity * cost_val * surcharge_factor

            final_cost += price  # Increasing the final cost amount
            current_minute += 1
            count += 1

            # Checking if the current minute is in peak time and if the previous minute (i.e., is_current_minute_peak)
            # was not peak, if so the time has moved from off off peak to peak and the cost needs to be recalculated
            if self.is_peak(current_minute) and not is_current_minute_peak:
                cost = base_price / (time_required + 1) / 100
                cost_val = cost
            # Checking if the current minute is in off peak time and if the previous minute (i.e., is_current_minute_
            # peak) was peak, if so the time has moved from off peak to off peak and the cost needs to be recalculated
            elif not self.is_peak(current_minute) and is_current_minute_peak:
                cost = base_price / (time_required + 1) / 100
                cost_val = cost/2

        return round(final_cost, 2)

    def time_calculation(self, initial_state, final_state, capacity, power):
        """
        time_calculation method used to determine the time it would take to charge the car battery from the
        initial SoC to the final SoC, as per the battery's capacity and the power supply
        :param initial_state: the initial state of charge of the car battery (int)
        :param final_state: the final state of charge of the car battery (int)
        :param capacity: the capacity of the car battery in kWh (int)
        :param power: the power supplied to the car battery via the charging outlet in kW (int)
        :return: the time taken to charge the car as per the passed in arguments
        """
        # Converting values to floats for time calculation
        initial_state = float(initial_state)
        final_state = float(final_state)
        capacity = float(capacity)
        power = float(power)
        time = (final_state - initial_state) / 100 * capacity / power   # Performing time calculation
        return round(time * 60, 2)

    def get_date_surcharge(self, date, code):
        """
        get_date_surcharge method is used to determine if the given post code has a public holiday or school holidays
        on the given date, or simply if the given date is a weekday. This allows us to determine what the surcharge
        should be on this date
        :param date: the date that the charging will take place (string)
        :param code: the post code of the area where charging will occur (int)
        :return: a boolean that is True if the date is a public holiday at the given post code, or a week day and False
        otherwise
        """
        # Determining state based off post code
        try:
            if 2000 <= code <= 2599 or 2619 <= code <= 2899 or 2921 <= code <= 2999:
                state = "nsw"
            elif 2600 <= code <= 2618 or 2900 <= code <= 2920:
                state = "act"
            elif 3000 <= code <= 3999:
                state = "vic"
            elif 4000 <= code <= 4999:
                state = "qld"
            elif 5000 <= code <= 5799:
                state = "sa"
            elif 6000 <= code <= 6797:
                state = "wa"
            elif 7000 <= code <= 7799:
                state = "tas"
            elif 800 <= code <= 899:
                state = "nt"
            else:
                # If the post code is not in any of the above ranges, it does not exist
                raise InvalidInputException
        except InvalidInputException:
            return -1

        # Checking if the date is a school holiday or weekday before the public holiday API call is made to save time
        # for the user
        if not self.is_date_in_school_term(date, state) or self.is_date_weekday(date):
            return 1.1

        # Determining the states (if any) that have a public holiday on this date
        states_list = self.get_date_data(date)

        if state in states_list:
            # If the supplied post code's state is in the state list, this date is a public holiday
            return 1.1
        return 1

    def is_date_weekday(self, date):
        """
        is_date_weekday method is used to determine whether the given date is weekday
        :param date: the date that the charging will take place (string)
        :return: a boolean representing whether or not the supplied date is a week day
        """
        date = date.split('/')
        date.reverse()
        date_time = datetime.datetime(int(date[0]), int(date[1]), int(date[2]))
        return date_time.weekday() < 5

    def is_date_in_school_term(self, date, state):
        """
        is_date_in_school_holiday method is used to determine whether the given date is school holiday in given state
        :param date: the date that the charging will take place (string)
        :param state: the state that the charging will take place (string)
        :return: a boolean which represents whether or not the given date is in the school term and i.e., whether or not
        it's a school holiday. This method only considers term dates from 2021 and it is assumed (for an approximation)
        that these dates will be the same for each year.
        """
        path = (Path(__file__) / '../../data/termdates.json').resolve()  # Getting absolute path of termdates.json
        # Opening file and reading data
        f = open(path)
        data = json.load(f)
        data = data["data"]
        for info in data:
            # Getting term dates for specific state (as each state has different term dates)
            if info["state"] == state:
                # Converting passed in date to a datetime object
                current_date = date.split("/")
                current_date = datetime.datetime(day=int(current_date[0]), month=int(current_date[1]), year=int(current_date[2]))
                # Go through each date range in the list to check each term
                for d in info["dates"]:
                    # Converting the date ranges into datetime objects
                    term_start = d[0].split("/")
                    term_end = d[1].split("/")
                    term_start_date = datetime.datetime(day=int(term_start[0]), month=int(term_start[1]), year=int(term_start[2]))
                    term_end_date = datetime.datetime(day=int(term_end[0]), month=int(term_end[1]), year=int(term_end[2]))

                    # Checking if passed in date is in the school term
                    if term_start_date <= current_date <= term_end_date:
                        return True
        return False

    def get_date_data_api(self):
        """
        get_date_data_api method is used to retrieve the list of public holiday across states in Australia
        :return: this method returns the response of the call to the public holiday api, and will return None if the
        returned response has some kind of an issue
        """
        response = requests.get(self.public_holiday_api_url)
        if response.ok:
            return response
        else:
            return None

    def get_date_data(self, date):
        """
        get_date_data method is used to get a list of all the public holiday dates for each state from an Aus Gov API,
        and returns the list of states that has the supplied date as a public holiday
        :param date: the date that the charging will take place (string)
        :return: an empty list if no states have the date as a public holiday, or simply a list containing the states
        that do have this date as a public holiday
        """
        # Accessing API data
        response = self.get_date_data_api()
        # Return -1 if response is None
        if response is None:
            return -1

        data = json.loads(response.content)["result"]["records"]  # Using json to convert the data to a python dict
        # Converting passed in date to required format for API data (i.e., 01/01/2021 -> 20210101)
        date = date.split('/')
        date.reverse()
        date = "".join(date)

        # Determining states that have the supplied date as a public holiday
        states_with_public_holiday = []
        for obj in data:
            if obj["Date"] == str(date):
                states_with_public_holiday.append(obj["Jurisdiction"])

        return states_with_public_holiday

    def get_next_date(self, date):
        """
        get_next_date method determines the next date based on the current date
        :param date: the current date (string)
        :return: the date following the current date
        """
        # Getting the date ready for the datetime class
        if "-" in date:
            date = date.split('-')
        else:
            date = date.split('/')

        # If the value in the first position is not 4 digits, the date needs to be reversed as the year is not first
        if len(date[0]) != 4:
            date.reverse()

        date_time_val = datetime.datetime(day=int(date[2]), month=int(date[1]), year=int(date[0]))
        date_time_val += datetime.timedelta(days=1)   # Adding one day to this date
        return date_time_val.strftime("%d/%m/%Y")  # Returning the following date in the correct format

    def get_reference_date(self, date):
        """
        get_reference_date method is used to determine the date argument in the most recent year in which it has already
        passed (i.e., 25/12/2021 -> 25/12/2020)
        :param date: the date that the charging will take place (string)
        :return: the reference date as per the date passed in such that it is the exact same date in the soonest year
        where it has passed
        """
        reference_year = 2021
        date = date
        date = date.split("/")
        date.reverse()
        date_time_val = datetime.datetime(year=int(date[0]), month=int(date[1]), day=int(date[2]))

        # If the date is in the future but still in the year 2021, make the reference dates from 2018 to 2020
        if datetime.datetime.now().date() - datetime.timedelta(days=1) <= date_time_val.date() and date[0] == "2021":
            return date_time_val.replace(year=2020).strftime("%d/%m/%Y")

        year_difference = int(date[0]) - reference_year

        try:
            # Determine if the future date results in a date in 2021 that has still not yet passed
            # If this is the case, the reference date should be in 2020
            reference_date = date_time_val.replace(year=date_time_val.year - year_difference)
            if reference_date.date() >= datetime.datetime.now().date() - datetime.timedelta(days=1):
                return date_time_val.replace(year=2020).strftime("%d/%m/%Y")
            return reference_date.strftime("%d/%m/%Y")
        except ValueError:
            # This exception is raised when a leap year date has been passed in but doesn't exist in 2021
            # Simply set the date to be 28/02 instead
            return date_time_val.replace(month=2, day=28, year=date_time_val.year - year_difference).strftime("%d/%m/%Y")

    def get_minute_from_start_time(self, start_time):
        """
        get_minute_from_start_time method used to determine the current minute of the day (out of 1440) based on the
        start time
        :param start_time: the start time that the charging begins
        :return: an integer that represents the current minute of the day
        """
        time = start_time.split(":")
        minutes = int(time[0]) * 60 + int(time[1])
        return minutes

    def convert_time_to_minutes_passed(self, time):
        """
        convert_time_to_minutes_passed method is used to convert given time into single hours and minutes
        :param time: the time that the charging will take place (string)
        """
        time = time.split(":")
        hours = int(time[0])
        mins = int(time[1])
        hours *= 60
        return hours + mins

    def is_peak(self, inputMinute):
        """
        is_peak method used to determine if the current minute is in the peak period
        :param inputMinute: the minute being checked
        :return: a boolean that is True if the current minute is in the peak period and False otherwise
        """
        return 360 <= inputMinute < 1080

    def process_date(self, date):
        """
        process_date method used to process given date and return to our expected format.
        :param date: the date that the charging will take place (string)
        :return: the date is returned in a format that is appropriate for the weather api
        """
        date = date.split("/")
        date.reverse()
        date[0] += "-"
        date[1] += "-"
        return ''.join(date)

    def get_weather_data_api(self, location_id, date):
        """
        get_weather_data_api method is retrieve weather details at particular location and date
        :param date: the date that the charging will take place (string)
        :param location_id: the id of the location that the charging will take place (string)
        :return: this method returns the response of the call to the weather api, and will return None if the
        returned response has some kind of an issue
        """
        weather_api = self.weather_api_url + location_id + "&date=" + date
        response = requests.get(weather_api)
        if response.ok:
            return response
        else:
            return None

    def get_date_solar_data(self, location_id, start_date, return_values):
        """
        get_date_solar_data method is used to retrieve the solar data for given date
        :param start_date: the start date that the charging will take place (string)
        :param location_id: the id of the location that the charging
        will take place (string)
        :param return_values: the expected return value in format ["date", "sunrise",
        "sunset", "sunHours", "hourlyWeatherHistory"]
        :return: the return value of this method is a list of the values from the api call as specified in the
        return_values input argument
        """
        date = self.process_date(start_date)
        response = self.get_weather_data_api(location_id, date)
        if response is None:
            return -1

        data = json.loads(response.content)
        output = []
        for value in return_values:
            if value == "date":
                output.append(date)  # If the processed date value is required, do not attempt to retrieve from json
            else:
                output.append(data[value])
        return output

    def get_date_daylight_hours(self, date, sunrise, sunset):
        """
        get_date_daylight_hours method is used to calculate and return the daylight duration from sunrise to sunset
        in given date
        :param date: the date that the charging will take place (string)
        :param sunrise: the sunrise time in given date
        :param sunset: the sunset time in given date
        :return: the number of hours that were daylight for the given date
        """
        date = date.split("-")
        sunrise_time = sunrise.split(":")
        sunset_time = sunset.split(":")

        sunrise_datetime = datetime.datetime(year=int(date[0]), month=int(date[1]), day=int(date[2]),
                                             hour=int(sunrise_time[0]), minute=int(sunrise_time[1]),
                                             second=int(sunrise_time[2]))
        sunset_datetime = datetime.datetime(year=int(date[0]), month=int(date[1]), day=int(date[2]),
                                            hour=int(sunset_time[0]), minute=int(sunset_time[1]),
                                            second=int(sunset_time[2]))

        daylight_hours = str(sunset_datetime - sunrise_datetime)
        daylight_hours = daylight_hours.split(":")
        hours = int(daylight_hours[0]) * 60
        mins = int(daylight_hours[1])
        return hours + mins

    def get_location_id_api(self, post_code):
        """
        get_location_id_api method used to retrieve location details for given postcode
        :param post_code: the post_code that user wants to retrieve details (string)
        :return: this method returns the response of the call to the location api, and will return None if the
        returned response has some kind of an issue
        """
        post_code_api = self.location_api_url + str(post_code)

        response = requests.get(post_code_api)
        if response.ok:
            return response
        else:
            return None

    def get_location_id(self, post_code, suburb):
        """
        get_location_id method used to retrieve location id for given postcode
        :param post_code: the post_code that user wants to retrieve details (string)
        :param suburb: the suburb that user wants to retrieve location id because one postcode can have multiple
         suburbs under their code(string)
        """
        response = self.get_location_id_api(post_code)
        if response is None:
            return -1

        data = json.loads(response.content)
        # Finding the id based on the suburb passed in
        for d in data:
            if d["name"] == suburb.upper():
                return d["id"]
        return -1

    def calculate_solar_energy_savings(self, initial_state, final_state, capacity, power, cost, start_time, start_date, post_code, suburb):
        """
        calculate_solar_energy_savings method used to calculate the total saving from solar energy generated
        :param initial_state: the initial state of charge of the car battery (int)
        :param final_state: the final state of charge of the car battery (int)
        :param capacity: the capacity of the car battery in kWh (int)
        :param power: the power supplied to the car battery via the charging outlet in kW (int)
        :param start_time: the time at which charging will begin (string)
        :param start_date: the date that the charging will begin (string)
        :param post_code: the post code of the area where charging will occur (string)
        :param suburb: the suburb that user wants to retrieve details
        :return: the savings that the user receives due to energy gained from the sun via solar panels
        """
        count = 0   # Holds the total count of the minutes that have been processed in the calculation
        savings = 0    # Represents the savings from energy generated in the current calculation
        daylight_minutes = 0    # Minutes that had daylight on the given date
        time_required = int(self.time_calculation(initial_state, final_state, capacity, power))
        current_minute = self.get_minute_from_start_time(start_time)
        date_surcharge = self.get_date_surcharge(start_date, post_code)
        location_id = self.get_location_id(post_code, suburb)
        if location_id == -1:
            return -1

        # Getting solar data for given date
        solar_data = self.get_date_solar_data(location_id, start_date, ["date", "sunrise", "sunset", "sunHours"])
        if solar_data == -1:
            return -1

        date = solar_data[0]
        sunrise = solar_data[1]
        sunset = solar_data[2]
        si = solar_data[3]
        dl = self.get_date_daylight_hours(date, sunrise, sunset)
        sunrise_in_minutes = self.convert_time_to_minutes_passed(sunrise)
        sunset_in_minutes = self.convert_time_to_minutes_passed(sunset)

        # Beginning calculation
        while count < time_required:
            # If the current minute is 1440, the end of the day has been reached. Get the date of the succeeding date
            # and recalculate the required values for this new date
            if current_minute == 1440:
                date = self.get_next_date(date)
                date_surcharge = self.get_date_surcharge(date, post_code)
                solar_data = self.get_date_solar_data(location_id, date, ["date", "sunrise", "sunset", "sunHours"])
                if solar_data == -1:
                    return -1

                date = solar_data[0]
                sunrise = solar_data[1]
                sunset = solar_data[2]
                si = solar_data[3]
                dl = self.get_date_daylight_hours(date, sunrise, sunset)
                sunrise_in_minutes = self.convert_time_to_minutes_passed(sunrise)
                sunset_in_minutes = self.convert_time_to_minutes_passed(sunset)
                current_minute = 1  # Resetting current minute back to 1 as it is the first minute of the next day

            # If the current minute is within the sunrise and sunset, increase the daylight minutes
            if sunrise_in_minutes <= current_minute <= sunset_in_minutes:
                daylight_minutes += 1

            # Only perform the calculation if the current minute is in daylight, and perform it if the end of the day
            # has been reached or if the end of the required time to calculate has been reached
            if sunrise_in_minutes <= current_minute <= sunset_in_minutes and current_minute == sunset_in_minutes or \
                    (count == time_required - 1 and sunrise_in_minutes <= current_minute <= sunset_in_minutes):
                # Calculating savings from given sunlight charging session
                du = daylight_minutes/60
                dl_hours = dl/60
                energy_generated = si * du/dl_hours * 50 * 0.2
                current_cost = cost / 100 if self.is_peak(current_minute) else cost / (100 * 2)
                savings += (power * du - energy_generated) * current_cost * date_surcharge

            count += 1
            current_minute += 1

        return round(savings, 2)

    def get_preceding_dates_for_average(self, date):
        """
        get_preceding_dates_for_average method used to get average preceding date for given three dates in three years
        :param date: the given date that we would like to precede for average
        :return: a list of dates that are based around the date argument passed in, used to determine an average value
        for the savings from sun generation in dates that have yet to pass
        """
        new_date = date.split("/")
        year = int(new_date[2])
        date1 = new_date[0:2]
        date1[0] += "/"
        date1[1] += "/"
        date1.append(str(year-1))
        date1 = ''.join(date1)
        date2 = new_date[0:2]
        date2[0] += "/"
        date2[1] += "/"
        date2.append(str(year-2))
        date2 = ''.join(date2)
        return [date, date1, date2]

    def calculate_solar_energy_savings_from_any_date(self, initial_state, final_state, capacity, power, cost, start_time, start_date, post_code, suburb):
        """
        calculate_solar_energy_savings_from_any_date method used to calculate the total saving from solar energy for
        any given date
        :param initial_state: the initial state of charge of the car battery (int)
        :param final_state: the final state of charge of the car battery (int)
        :param capacity: the capacity of the car battery in kWh (int)
        :param power: the power supplied to the car battery via the charging outlet in kW (int)
        :param start_time: the time at which charging will begin (string)
        :param start_date: the date that the charging will begin (string)
        :param post_code: the post code of the area where charging will occur (string)
        :param suburb: the suburb that user wants to retrieve details
        :return: the savings that the user receives due to energy gained from the sun via solar panels, taking cloud
        coverage into account
        """
        location_id = self.get_location_id(post_code, suburb)   # Getting location id for weather API based off post code
        if location_id == -1:
            return -1

        # Determining if date has passed already such that if it has not, an average of past dates can be determined
        # instead
        passed_date = start_date.split("/")
        dt_check = datetime.datetime(day=int(passed_date[0]), month=int(passed_date[1]), year=int(passed_date[2]))
        if dt_check.date() < datetime.datetime.now().date() - datetime.timedelta(days=1):
            dates = [start_date]
        else:
            dates = self.get_preceding_dates_for_average(self.get_reference_date(start_date))   # Getting all dates for calc

        savings_from_solar_energy_generated = []  # Will store the energy generated in the time frame of each respective date

        for date in dates:
            charging_hours_spent_in_sunlight = 0    # Represents the charging hours that were in sunlight
            count = 0   # Represents the number of minutes covered in the current calculation
            savings = 0    # Represents the savings from energy generated in the current calculation
            daylight_minutes = 0    # Represents the number of charging minutes that occurred in daylight
            time_required = int(self.time_calculation(initial_state, final_state, capacity, power))
            time = self.get_minute_from_start_time(start_time)
            current_minute = time
            date_surcharge = self.get_date_surcharge(date, post_code)
            # Retrieving solar data from API (list contains the values required from the API call)
            solar_data = self.get_date_solar_data(location_id, date, ["date", "sunrise", "sunset", "sunHours",
                                                                            "hourlyWeatherHistory"])
            if solar_data == -1:
                return -1

            # Setting values
            date = solar_data[0]
            sunrise = solar_data[1]
            sunset = solar_data[2]
            si = solar_data[3]
            hourlyWeather = solar_data[4]
            dl = self.get_date_daylight_hours(date, sunrise, sunset)    # Determining dl in minutes
            sunrise_in_minutes = self.convert_time_to_minutes_passed(sunrise)   # Determining how many minutes have passed at sunrise
            sunset_in_minutes = self.convert_time_to_minutes_passed(sunset)  # Determining how many minutes have passed at sunset
            # Getting cloud coverage values
            hourlyWeather.sort(key=lambda x: x["hour"])     # Sorting hours
            cc = []
            for hour in hourlyWeather:
                cc.append(hour["cloudCoverPct"])

            while count < time_required:
                if current_minute == 1440:
                    # Resetting values for new day if charging takes place over more than one date
                    date = self.get_next_date(date)
                    date_surcharge = self.get_date_surcharge(date, post_code)
                    solar_data = self.get_date_solar_data(location_id, date, ["date", "sunrise", "sunset", "sunHours",
                                                                              "hourlyWeatherHistory"])
                    if solar_data == -1:
                        return -1

                    date = solar_data[0]
                    sunrise = solar_data[1]
                    sunset = solar_data[2]
                    si = solar_data[3]
                    hourlyWeather = solar_data[4]
                    dl = self.get_date_daylight_hours(date, sunrise, sunset)
                    sunrise_in_minutes = self.convert_time_to_minutes_passed(sunrise)
                    sunset_in_minutes = self.convert_time_to_minutes_passed(sunset)
                    hourlyWeather.sort(key=lambda x: x["hour"])
                    cc = []
                    for hour in hourlyWeather:
                        cc.append(hour["cloudCoverPct"])
                    current_minute = 1  # Resetting current minute back to 1 as it is the first minute of the next day
                    time = sunrise_in_minutes

                if sunrise_in_minutes <= current_minute <= sunset_in_minutes:
                    daylight_minutes += 1

                # If the current minute has reached the end of an hour, and the minute is still in daylight, calculate
                # the hour's generated energy or if the number of minutes required for the calculation is reached, and
                # this minute is in daylight, calculate the energy savings (this is for partial hours)
                if sunrise_in_minutes <= current_minute <= sunset_in_minutes and (current_minute + 1) % 60 == 0 \
                        or current_minute == sunset_in_minutes \
                        or (count == time_required - 1 and sunrise_in_minutes <= current_minute <= sunset_in_minutes):
                    charging_hours_spent_in_sunlight += 1
                    dl_hours = dl/60
                    hour = math.floor((charging_hours_spent_in_sunlight*60 + time)/1440 * 24)   # Getting current hour of the day
                    current_cc = cc[hour]
                    charging_mins_in_hour = daylight_minutes/60
                    energy_generated = si * charging_mins_in_hour/dl_hours * (1 - current_cc/100) * 50 * 0.2
                    current_cost = cost/100 if self.is_peak(current_minute) else cost/(100*2)
                    savings += (power*charging_mins_in_hour - energy_generated) * current_cost * date_surcharge
                    daylight_minutes = 0

                count += 1
                current_minute += 1

            savings_from_solar_energy_generated.append(savings)
        return sum(savings_from_solar_energy_generated) / len(savings_from_solar_energy_generated)

    def format_time(self, time):
        """
        format_time method used to format the given time
        :param time: given time that will be formatted
        :return: formatted time string that is appealing and understandable to a user
        """
        seconds = int((time - int(time)) * 60)
        time = int(time)
        days = time//1440
        remaining_mins = time % 1440
        hours = remaining_mins // 60
        mins = time - (days*1440) - (hours*60)
        if days == 0 and hours == 0 and mins == 0:
            return str(seconds) + " seconds."
        elif days == 0 and hours == 0:
            return str(mins) + " minutes and " + str(seconds) + " seconds."
        elif days == 0:
            return str(hours) + " hours and " + str(mins) + " minutes and " + str(seconds) + " seconds."
        else:
            if days == 1:
                return str(days) + " day, " + str(hours) + " hours and " + str(mins) + " minutes and " + \
                    str(seconds) + " seconds."
            return str(days) + " days, " + str(hours) + " hours and " + str(mins) + " minutes and " + \
                str(seconds) + " seconds."


class InvalidInputException(Exception):
    pass
