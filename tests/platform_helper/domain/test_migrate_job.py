from unittest.mock import Mock

class ScheduledJob:
    def __init__(self, sfn_client):
        self.sfn_client = sfn_client
        
    def disable_schedule(name, environment):
        return "done"
    
    def get_schedule(name, environment):
        return None

def test_disable_copilot_schedule():
    pass
    mock_client = Mock()
    
    ScheduledJob.disable_schedule("my-job", "dev")
    
    result = ScheduledJob.get_schedule("my-job", "dev")
    
    assert result is None