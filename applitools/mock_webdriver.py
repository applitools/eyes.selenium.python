class MockSwitchTo:
    def __init__(self):
        pass

    def default_contennt(self):
        pass

    def frames(self, frame_chain):
        pass


class MockWebDriver:
    def __init__(self):
        self.viewport_size = None
        self.capabilities = {'takesScreenshot': True}

    # noinspection PyMethodMayBeStatic
    def get_frame_chain(self):
        return []

    # noinspection PyMethodMayBeStatic
    def execute_script(self, script):
        return None

    def get_window_size(self):
        return self.viewport_size

    def quit(self):
        pass

    @property
    def switch_to(self):
        return MockSwitchTo()





