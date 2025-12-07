import app


def test_hello_default() -> None:
    assert app.hello() == "hello, world"
