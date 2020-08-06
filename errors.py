class RepetitionError(Exception):
     pass

class WrongCommandError(Exception):
     pass

class EventTooEarlyError(Exception):
     pass

class NoTimeZoneError(Exception):
     pass

class EventDoesNotExistError(Exception):
     pass

class TooManyEventsError(Exception):
     pass