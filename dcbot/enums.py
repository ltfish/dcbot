
class CTFFloorStatusEnum:
    """
    Everyone starts with neutral (which is the default status). Changes to WantsToGo once they tells the bot that they
    wants to be on the floor. Changes to OnTheFloor once Giovanni approves it.
    """
    Neutral = 0
    WantsToGo = 1
    OnTheFloor = 2

    @staticmethod
    def to_string(intent):
        if intent == CTFFloorStatusEnum.Neutral:
            return "Neutral"
        elif intent == CTFFloorStatusEnum.WantsToGo:
            return "Wants to go"
        elif intent == CTFFloorStatusEnum.OnTheFloor:
            return "On the floor"
        else:
            return "Unknown intent %d" % intent
