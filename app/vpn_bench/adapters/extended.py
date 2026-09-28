from .singbox import SingBoxAdapter


class SingBoxLXAdapter(SingBoxAdapter):
    """sing-box-lx backend with XHTTP/AWG and other lx build features."""

    def __init__(self, binary: str = "sing-box-lx", work_dir: str = "/tmp/vpn-bench") -> None:
        super().__init__(
            binary=binary,
            work_dir=work_dir,
            allow_extended_transports=True,
        )


class SingBoxExtendedAdapter(SingBoxAdapter):
    """sing-box-extended backend with its additional protocol/transport set."""

    def __init__(self, binary: str = "sing-box-extended", work_dir: str = "/tmp/vpn-bench") -> None:
        super().__init__(
            binary=binary,
            work_dir=work_dir,
            allow_extended_transports=True,
        )
