import logging
import json
import requests
from datetime import datetime

from homeassistant.const import STATE_UNKNOWN
from .const import DEFAULT_TIMEOUT, DIVERA_STATUS_URL, DIVERA_URL
from .data import StateNotFoundError, Vehicle

_LOGGER = logging.getLogger(__name__)


class DiveraData:
    def __init__(self, hass, api_key):
        self._hass = hass

        self.success = False
        self.latest_update = None

        self.data = None

        if api_key != "":
            self.api_key = api_key

    async def async_update(self):
        return await self._hass.async_add_executor_job(self._update)

    def _update(self):
        timestamp = datetime.now()

        if not self.api_key:
            _LOGGER.exception("No update possible")
        else:
            params = {"accesskey": self.api_key}
            try:
                response = requests.get(
                    DIVERA_URL, params=params, timeout=DEFAULT_TIMEOUT
                )
                self.data = response.json()
                self.success = response.status_code == 200
            except requests.exceptions.HTTPError as ex:
                _LOGGER.error("Error: {}".format(str(ex)))
                self.success = False
            else:
                self.latest_update = timestamp
            _LOGGER.debug("Values updated at %s", self.latest_update)

    def get_user(self):
        """returns user_data"""
        data = {}
        data["firstname"] = self.data["data"]["user"]["firstname"]
        data["lastname"] = self.data["data"]["user"]["lastname"]
        data["fullname"] = data["firstname"] + " " + data["lastname"]
        data["email"] = self.data["data"]["user"]["email"]
        return data

    def get_user(self, user_id):
        """returns user_data"""
        data = {}
        data["firstname"] = self.data["data"]["cluster"]["consumer"][str(user_id)]["firstname"]
        data["lastname"] = self.data["data"]["cluster"]["consumer"][str(user_id)]["lastname"]
        data["fullname"] = data["firstname"] + " " + data["lastname"]
        return data

     def get_state_id(self):
        """returns state.id of user"""
        id = self.data["data"]["status"]["status_id"]
        return id

    def get_user_state(self):
        """returns state.name of user"""
        id = self.data["data"]["status"]["status_id"]
        state_name = self.data["data"]["cluster"]["status"][str(id)]["name"]
        return state_name

    def get_user_state(self, user_id):
        """returns state.name of user.id"""
        state_id = self.data["data"]["monitor"]["3"][str(user_id)]["status"]
        state_name = self.data["data"]["cluster"]["status"][str(state_id)]["name"]
        return state_name

    def get_user_state_attributes(self):
        """return aditional information of state"""
        data = {}
        timestamp = self.data["data"]["status"]["status_set_date"]
        data["timestamp"] = datetime.fromtimestamp(timestamp)
        data["id"] = self.data["data"]["status"]["status_id"]
        return data

    def get_user_state_attributes(self, user_id):      
        """return aditional information of state"""
        data = {}
        timestamp = self.data["data"]["monitor"]["3"][str(user_id)]["ts"]
        data["timestamp"] = datetime.fromtimestamp(timestamp)
        data["id"] = self.data["data"]["monitor"]["3"][str(user_id)]["id"]
        return data

    def get_last_alarm(self):
        """return informations of last alarm"""
        sorting_list = self.data["data"]["alarm"]["sorting"]
        if len(sorting_list) > 0:
            last_alarm_id = sorting_list[0]
            alarm = self.data["data"]["alarm"]["items"][str(last_alarm_id)]
            return alarm["title"]
        else:
            return STATE_UNKNOWN

    def get_last_alarm_attributes(self):
        """return aditional information of last alarm"""
        sorting_list = self.data["data"]["alarm"]["sorting"]
        if len(sorting_list) > 0:
            last_alarm_id = sorting_list[0]
            alarm = self.data["data"]["alarm"]["items"][str(last_alarm_id)]
            groups = map(self.__search_group, alarm["group"])
            return {
                "id": alarm["id"],
                "text": alarm["text"],
                "date": datetime.fromtimestamp(alarm["date"]),
                "address": alarm["address"],
                "latitude": str(alarm["lat"]),
                "longitude": str(alarm["lng"]),
                "groups": list(groups),
                "priority": alarm["priority"],
                "closed": alarm["closed"],
                "new": alarm["new"],
                "self_addressed": alarm["ucr_self_addressed"],
            }
        else:
            return {}



    def get_group_name_by_id(self, group_id):
        """returns group.name from given group.id"""
        group = self.data["data"]["cluster"]["group"][str(group_id)]
        return group["name"]

    def get_vehicles(self):
        """return list of vehicles"""
        raw_vehicles = self.data["data"]["cluster"]["vehicle"]
        vehicles = []
        for id in raw_vehicles:
            v = raw_vehicles[id]
            vehicles.append(Vehicle(v))
        return vehicles

    def get_ucr_0(self):
        """return if of user"""
        return list(self.data["data"]["ucr"])[0]

    def get_state_id_by_name(self, name):
        """returns state.id from given state.name"""
        for id in self.data["data"]["cluster"]["statussorting"]:
            state_name = self.data["data"]["cluster"]["status"][str(id)]["name"]
            if state_name == name:
                return id
        raise StateNotFoundError()

    def get_all_state_name(self):
        """returns available state.names"""
        states = []
        for id in self.data["data"]["cluster"]["statussorting"]:
            state_name = self.data["data"]["cluster"]["status"][str(id)]["name"]
            states.append(state_name)
        return states

    def get_user_state_id(self):
        """returns state.id of user"""
        id = self.data["data"]["status"]["status_id"]
        return id

    def set_state(self, state_id):
        payload = json.dumps({"Status": {"id": state_id}})
        headers = {"Content-Type": "application/json"}

        if not self.api_key:
            _LOGGER.exception("state can not be set. api-key is missing")
        else:
            params = {"accesskey": self.api_key}
            try:
                response = requests.post(
                    DIVERA_STATUS_URL,
                    params=params,
                    headers=headers,
                    timeout=DEFAULT_TIMEOUT,
                    data=payload,
                )
                if response.status_code != 200:
                    _LOGGER.error("Error while setting the state")
            except requests.exceptions.HTTPError as ex:
                _LOGGER.error("Error: {}".format(str(ex)))
