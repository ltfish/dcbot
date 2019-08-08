
class CTFFloorStatusEnum:
    """
    Everyone starts with neutral (which is the default status). Changes to WantsToGo once they tells the bot that they
    wants to be on the floor. Changes to OnTheFloor once Giovanni approves it.
    """
    Neutral = 0
    WantsToGo = 1
    OnTheFloor = 2
