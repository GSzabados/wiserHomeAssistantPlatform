"""
Drayton Wiser Compoment for Wiser System

Includes Climate and Sensor Devices

https://github.com/asantaga/wiserHomeAssistantPlatform
Angelo.santagata@gmail.com
"""

import json
import logging
import time
from socket import timeout
from threading import Lock

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.const import (CONF_HOST, CONF_MINIMUM, CONF_PASSWORD,
                                 CONF_SCAN_INTERVAL)
from homeassistant.helpers.discovery import load_platform

_LOGGER = logging.getLogger(__name__)
NOTIFICATION_ID = 'wiser_notification'
NOTIFICATION_TITLE = 'Wiser Component Setup'
CONF_BOOST_TEMP_DEFAULT = '20'
CONF_BOOST_TEMP = 'boost_temp'
CONF_BOOST_TEMP_TIME = 'boost_time'

VERSION = '1.3.1'
DOMAIN = 'wiser'
DATA_KEY = 'wiser'

PLATFORM_SCHEMA = vol.Schema({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=300): cv.time_period,
    vol.Optional(CONF_MINIMUM, default=-5): vol.All(vol.Coerce(int)),
    vol.Optional(CONF_BOOST_TEMP, default=20): vol.All(vol.Coerce(int)),
    vol.Optional(CONF_BOOST_TEMP_TIME, default=30): vol.All(vol.Coerce(int))
})

def setup(hass, config):
    hub_host = config[DOMAIN][0][CONF_HOST]
    password = config[DOMAIN][0][CONF_PASSWORD]
    scan_interval = config[DOMAIN][0][CONF_SCAN_INTERVAL].total_seconds()
    minimum_temp = config[DOMAIN][0][CONF_MINIMUM]
    boost_temp = config[DOMAIN][0][CONF_BOOST_TEMP]
    boost_time = config[DOMAIN][0][CONF_BOOST_TEMP_TIME]

    _LOGGER.info("Wiser setup with HubIp =  {}".format(hub_host))
    hass.data[DATA_KEY] = WiserHubHandle(hub_host, password, scan_interval,
                                         minimum_temp, boost_temp, boost_time)

    _LOGGER.info("Wiser Component Setup Completed")

    load_platform(hass, 'climate', DOMAIN, {}, config)
    load_platform(hass, 'sensor', DOMAIN, {}, config)
    load_platform(hass, 'switch', DOMAIN, {}, config)
    return True


"""
Single parent class to coordindate the rest calls to teh Heathub
"""


class WiserHubHandle:
    def __init__(self, ip, secret, scan_interval, minimum_temp,
                 boost_temp, boost_time):
        self.scan_interval = scan_interval
        self.ip = ip
        self.secret = secret
        self.wiserHubInstance = None
        self.mutex = Lock()
        self.minimum_temp = minimum_temp
        self.last_updated = time.time()
        self.boost_temp = boost_temp
        self.boost_time = boost_time
        _LOGGER.info("min temp = {}".format(self.minimum_temp))

    def get_hub_data(self):
        from wiserHeatingAPI import wiserHub
        if self.wiserHubInstance is None:
            self.wiserHubInstance = wiserHub.wiserHub(self.ip, self.secret)
        return self.wiserHubInstance

    def get_minimum_temp(self):
        return self.minimum_temp

    def force_next_scan(self):
        # When this function is called, the last_updated variable is forced
        # back so that we force a refresh
        _LOGGER.debug("force_next_scan requested")
        self.last_updated=self.last_updated - self.scan_interval*2

    def update(self):
        _LOGGER.info("Update Requested")
        from wiserHeatingAPI import wiserHub
        if self.wiserHubInstance is None:
            self.wiserHubInstance = wiserHub.wiserHub(self.ip, self.secret)
        with self.mutex:
            if (time.time() - self.last_updated) >= self.scan_interval:
                _LOGGER.debug("**********************************************")
                _LOGGER.info("Scan Interval exceeeded, updating Wiser " +
                             " DataSet from hub")
                _LOGGER.debug("**********************************************")
                try:
                    self.wiserHubInstance.refreshData()
                except timeout as timeoutex:
                    _LOGGER.error("Timed out whilst connecting to {}, with " +
                                  " error {}".format(self.ip, str(timeoutex)))
                    hass.components.persistent_notification.create(
                        "Error: {}" +
                        "<br /> You will need to restart Home Assistant " +
                        " after fixing.".format(ex), title=NOTIFICATION_TITLE,
                        notification_id=NOTIFICATION_ID)
                    return False
                except json.decoder.JSONDecodeError as JSONex:
                    _LOGGER.error(
                        "Data not JSON when getting Data from hub, " +
                        "did you enter the right URL? error {}".
                        format(str(JSONex)))
                    hass.components.persistent_notification.create(
                        "Error: {}" +
                        "<br /> You will need to restart Home Assistant " +
                        " after fixing.".format(ex), title=NOTIFICATION_TITLE,
                        notification_id=NOTIFICATION_ID)
                    return False
                self.last_updated = time.time()
                return True
            else:
                _LOGGER.info("Skipping update (data already gotten within " +
                             " scan interval)")

    def set_room_temperature(self, room_id, target_temperature):
        _LOGGER.info("set {} to {}".format(room_id, target_temperature))
        from wiserHeatingAPI import wiserHub
        if self.wiserHubInstance is None:
            self.wiserHubInstance = wiserHub.wiserHub(self.ip, self.secret)
        with self.mutex:
            self.wiserHubInstance.setRoomTemperature(room_id,
                                                       target_temperature)
            self.force_next_scan()
            return True

    def set_room_mode(self, room_id, mode):
        from wiserHeatingAPI import wiserHub
        if self.wiserHubInstance is None:
            self.wiserHubInstance = wiserHub.wiserHub(self.ip, self.secret)
        with self.mutex:
            self.wiserHubInstance.setRoomMode(room_id, mode, self.boost_temp,
                                                self.boost_time)
            self.force_next_scan()
            return True

    def set_away_mode(self, away, away_temperature):
        from wiserHeatingAPI import wiserHub
        if self.wiserHubInstance is None:
            self.wiserHubInstance = wiserHub.wiserHub(self.ip, self.secret)
        mode = 'AWAY' if away else 'HOME'
        with self.mutex:
            self.wiserHubInstance.setHomeAwayMode(mode, away_temperature)
            self.force_next_scan()
            return True
