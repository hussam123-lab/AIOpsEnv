from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField
from wtforms.validators import DataRequired, ValidationError, Optional
import datetime
import requests
import json


# validation for form inputs
class Calculator_Form(FlaskForm):
    # this variable name needs to match with the input attribute name in the html file
    # you are NOT ALLOWED to change the field type, however, you can add more built-in validators and custom messages
    BatteryPackCapacity = StringField("Battery Pack Capacity", [DataRequired()])
    InitialCharge = StringField("Initial Charge", [DataRequired()])
    FinalCharge = StringField("Final Charge", [DataRequired()])
    StartDate = DateField("Start Date", [DataRequired("Data is missing or format is incorrect")], format='%d/%m/%Y')
    StartTime = TimeField("Start Time", [DataRequired("Data is missing or format is incorrect")], format='%H:%M')
    ChargerConfiguration = StringField("Charger Configuration", [DataRequired()])
    PostCode = StringField("Post Code", [DataRequired()])
    Suburb = StringField("Suburb", [DataRequired()])

    # use validate_ + field_name to activate the flask-wtforms built-in validator
    # this is an example for you
    def validate_BatteryPackCapacity(self, field):
        # error if data is not an integer
        if field.data is None:
            raise ValidationError('Field data is none')

        try:
            _ = int(field.data)
        except ValueError:
            raise ValueError("Battery capacity must be an integer")

        # error if data is less than or equal to 0
        if int(field.data) <= 0:
            raise ValueError("Battery capacity must be greater than 0")


    # validate initial charge here
    def validate_InitialCharge(self, field):
        # another example of how to compare initial charge with final charge
        # you may modify this part of the code
        if field.data is None:
            raise ValidationError('Field data is none')

        # error if data is not an integer
        try:
            _ = int(field.data)
        except ValueError:
            raise ValueError("Initial charge must be an integer")

        # error if data is not between 0 and 99
        if int(field.data) < 0:
            raise ValueError("Initial charge must be greater than or equal to 0")
        elif int(field.data) >= 100:
            raise ValueError("Initial charge must be less than 100")

    # validate final charge here
    def validate_FinalCharge(self, field):
        if field.data is None:
            raise ValidationError('Field data is none')

        # error if data is not an integer
        try:
            _ = int(field.data)
        except ValueError:
            raise ValueError("Final charge must be an integer")

        # error if data is not between 1 and 100
        if int(field.data) <= 0:
            raise ValueError("Final charge must be greater than 0")
        elif int(field.data) > 100:
            raise ValueError('Final charge cannot be more than 100')
        # check if initial charge is an integer if so, error if data is less than initial charge
        if self.InitialCharge.data.isdigit():
            if int(field.data) <= int(self.InitialCharge.data):
                raise ValueError('Final charge must be greater than initial charge')

    # validate start date here
    def validate_StartDate(self, field):
        if field.data is None:
            raise ValidationError('Field data is none')

        # error if date is before 01/07/2008
        elif int(field.data.year) == 2008 and int(field.data.month) < 7:
            raise ValueError("Start date must be a date after 30/06/2008")
        # error if year is before 2008
        elif int(field.data.year) < 2008:
            raise ValueError("Start date must be a date after 30/06/2008")
        # error if year is greater than 2999
        elif int(field.data.year) > 2999:
            raise ValueError("Start date must be a date before 01/01/3000")

        year = int(field.data.year)
        month = int(field.data.month)
        day = int(field.data.day)
        _ = datetime.datetime(year=year, month=month, day=day)

    # validate start time here
    def validate_StartTime(self, field):
        if field.data is None:
            raise ValidationError('Field data is none')
        # not sure if this is needed, seems to be caught by the wrong format
        elif int(field.data.hour) > 23:
            raise ValueError("Start time's hour must be a number from 0-23")
        elif int(field.data.hour) < 0:
            raise ValueError("Start time's hour must be a number from 0-23")
        elif int(field.data.minute) > 59:
            raise ValueError("Start time's minute must be a number from 0-59")
        elif int(field.data.minute) < 0:
            raise ValueError("Start time's minute must be a number from 0-59")

    # validate charger configuration here
    def validate_ChargerConfiguration(self, field):
        if field.data is None:
            raise ValidationError('Field data is none')

        # error if data is not an integer
        try:
            _ = int(field.data)
        except ValueError:
            raise ValueError("Charger configuration must be an integer")

        int_charger_config = int(field.data)

        # error if charger config is not between 1 and 8
        if int_charger_config > 8:
            raise ValueError("Charger configuration must be a number from 1-8")
        elif int_charger_config < 1:
            raise ValueError("Charger configuration must be a number from 1-8")

    # validate postcode here
    def validate_PostCode(self, field):
        if field.data is None:
            raise ValidationError('Field data is none')
        # error if data is not an integer
        try:
            _ = int(field.data)
        except ValueError:
            raise ValueError("Post code must be an integer")
        int_postcode = int(field.data)

        if int_postcode < 800 or 899 < int_postcode < 2000 or 2920 < int_postcode < 3000 or 5799 < int_postcode < 6000 or 6797 < int_postcode < 7000 or int_postcode > 7799:
            raise ValueError('Postcode does not exist')

    # validate suburb here
    def validate_Suburb(self, field):
        if field.data is None:
            raise ValidationError('Field data is none')

        # error if data is an integer
        if field.data != str(field.data):
            raise ValueError('Suburb cannot be a number')

        url = "http://118.138.246.158/api/v1/location?postcode=" + self.PostCode.data
        response = requests.get(url)
        data = json.loads(response.content)
        list_data = list(data)

        # check if 1st in list is statuscode(when wrong postcode)
        if list_data[0] != "statusCode":
            # check keys for name and if not equal to suburb name, raise error
            for d in data:
                if d["name"] != field.data.upper():
                    raise ValueError('Suburb not found in region specified by postcode')

