"""
Climate Platform Device for Wiser Rooms

https://github.com/asantaga/wiserHomeAssistantPlatform
Angelosantagata@gmail.com

"""
import logging
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import ClimateDevice
#from homeassistant.components.climate.const import (STATE_AUTO,
#                                                    SUPPORT_OPERATION_MODE,
#                                                    SUPPORT_TARGET_TEMPERATURE,
#                                                    HVAC_MODE_HEAT_COOL)
#
from homeassistant.components.climate.const import (HVAC_MODE_AUTO, SUPPORT_TARGET_TEMPERATURE, SUPPORT_PRESET_MODE, HVAC_MODE_HEAT_COOL)
from homeassistant.const import (ATTR_BATTERY_LEVEL, ATTR_TEMPERATURE,
                                 TEMP_CELSIUS)
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)
DOMAIN = 'wiser'

PRESET_MANUAL = 'Manual'
PRESET_BOOST = 'Boost'
PRESET_OVERRIDE = 'Override'
PRESET_AUTO = 'Schedule'

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the sensor platform."""
    handler = hass.data[DOMAIN]  # Get Handler

    handler.update()
    wiser_rooms = []

    """ Get Rooms """
    for room in handler.get_hub_data().getRooms():
        wiser_rooms.append(WiserRoom(room.get('id'), handler))
    add_devices(wiser_rooms)


""" Definition of WiserRoom """


class WiserRoom(ClimateDevice):

    def __init__(self, room_id, handler):
        """Initialize the sensor."""
        _LOGGER.info("Wiser Room Initialisation")
        self.handler = handler
        self.roomId = room_id
        self._hvac_modes_list = [HVAC_MODE_AUTO, HVAC_MODE_HEAT_COOL]
        self._preset_modes_list = [PRESET_AUTO, PRESET_BOOST]

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def should_poll(self):
        return True

    @property
    def state(self):
        state=self.handler.get_hub_data().getRoom(self.roomId).get('Mode')
        _LOGGER.info('State requested for room %s, state=%s', self.roomId,state)
        # TODO :  State can be Manual, Auto or Boost.. Need to see how to deal with boost
        if (state.lower() == "manual"):
            state = HVAC_MODE_HEAT_COOL
        else:
            state = HVAC_MODE_AUTO
        return state

    @property
    def name(self):
        return "Wiser " + self.handler.get_hub_data().getRoom(self.roomId). \
            get('Name')

    @property
    def temperature_unit(self):
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        temp = self.handler.get_hub_data().getRoom(self.roomId). \
                   get('CalculatedTemperature') / 10
        if temp < self.handler.get_minimum_temp():
            """ Sometimes we get really low temps (like -3000!),
                not sure why, if we do then just set it to -20 for now till i
                debug this.
            """
            temp = self.handler.get_minimum_temp()
        return temp

    @property
    def icon(self):
        return "mdi:oil-temperature"

    @property
    def hvac_mode(self):
        state = self.handler.get_hub_data().getRoom(self.roomId).get('Mode')
        if (state.lower() == "manual"):
            state = HVAC_MODE_HEAT_COOL
        if (state.lower()== "auto"):
            state = HVAC_MODE_AUTO
        return state

    def set_hvac_mode(self, hvac_mode):
        """Set new operation mode."""
        _LOGGER.debug("*******Setting Device Operation {} for roomId {}".
                      format(hvac_mode, self.roomId))
        # Convert HA heat_cool to manual as required by api
        if (hvac_mode == "heat_cool"):
            hvac_mode = "manual"
        self.handler.set_room_mode(self.roomId, hvac_mode)

        return True

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return self._hvac_modes_list

    @property
    def preset_mode(self):
        preset = self.handler.get_hub_data().getRoom(self.roomId).get('SetpointOrigin')
        if (preset.lower() == "fromboost"):
            preset = PRESET_BOOST
        else:
            if (preset.lower() == "frommanualoverride"):
                preset = PRESET_OVERRIDE
            else:
                if (preset.lower() == "frommanualmode"):
                    preset = PRESET_MANUAL
                else:
                    preset = PRESET_AUTO
        return preset

    def set_preset_mode(self, preset_mode):
        """Set new preset mode."""
        _LOGGER.debug("*******Setting Preset Mode {} for roomId {}".
                      format(preset_mode, self.roomId))
        #Convert HA preset to required api presets
        if (preset_mode.lower() == 'schedule'):
            preset_mode = 'auto'
        if (preset_mode.lower() == 'override' or preset_mode.lower() == 'manual'):
            preset_mode = 'manual'
        self.handler.set_room_mode(self.roomId, preset_mode)

        return True
        
    @property
    def preset_modes(self):
        """Return the list of available preset modes."""
        return self._preset_modes_list
      
    @property
    def target_temperature(self):
        return self.handler.get_hub_data().getRoom(self.roomId). \
                   get('CurrentSetPoint') / 10

    def update(self):
        _LOGGER.debug("*******************************************")
        _LOGGER.debug("WiserRoom Update requested")
        _LOGGER.debug("*******************************************")
        self.handler.update()

    """    https://github.com/asantaga/wiserHomeAssistantPlatform/issues/13 """

    @property
    def state_attributes(self):
        # Generic attributes
        attrs = super().state_attributes
        attrs['percentage_demand'] = self.handler.get_hub_data(). \
            getRoom(self.roomId).get('PercentageDemand')
        attrs['control_output_state'] = self.handler.get_hub_data(). \
            getRoom(self.roomId).get('ControlOutputState')
        attrs['set_point_origin'] = self.handler.get_hub_data(). \
            getRoom(self.roomId).get('SetpointOrigin')
        attrs['heating_rate'] = self.handler.get_hub_data(). \
            getRoom(self.roomId).get('HeatingRate')
        attrs['window_state'] = self.handler.get_hub_data(). \
            getRoom(self.roomId).get('WindowState')
        attrs['window_detection_active'] = self.handler.get_hub_data(). \
            getRoom(self.roomId).get('WindowDetectionActive')
        attrs['away_mode_supressed'] = self.handler.get_hub_data(). \
            getRoom(self.roomId).get('AwayModeSuppressed')

        return attrs

    """ Set temperature """

    def set_temperature(self, **kwargs):
        """Set new target temperatures."""
        if kwargs.get(ATTR_TEMPERATURE) is None:
            return False
        target_temperature = kwargs.get(ATTR_TEMPERATURE)
        _LOGGER.debug(
            "Setting Device Temperature for roomId {}, temperature {}".
                format(self.roomId, target_temperature))
        _LOGGER.debug("Value of wiserhub {}".format(self.handler))

        self.handler.set_room_temperature(self.roomId, target_temperature)

