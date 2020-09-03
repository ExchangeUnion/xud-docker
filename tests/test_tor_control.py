from stem.control import Controller


def test_1():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate("ieshi4Ea7phoo0ahvie6eingiev1Jeey")
        # controller.authenticate("test")
        bytes_read = controller.get_info("traffic/read")
        bytes_written = controller.get_info("traffic/written")

        print("My Tor relay has read %s bytes and written %s." % (bytes_read, bytes_written))

        controller.create_hidden_service("/root/.tor/hidden/xud", 8082)
