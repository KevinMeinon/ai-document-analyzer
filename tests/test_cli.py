from document_analyzer.main import _parse_args


def test_chat_is_a_supported_cli_command() -> None:
    assert _parse_args(["chat"]).command == "chat"


def test_server_remains_the_default_cli_command() -> None:
    args = _parse_args([])
    assert args.command == "serve"
    assert args.port == 8001
