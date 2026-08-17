from __future__ import annotations

import grpc

from spiritvpn.customer.v1.customer_pb2_grpc import CustomerAccessServiceStub


def build_customer_access_stub(
    *,
    target: str,
    client_cert_file: str,
    client_key_file: str,
    ca_file: str,
) -> CustomerAccessServiceStub:
    """Открывает mTLS-канал к spiritvpnd и возвращает стаб CustomerAccessService.

    Args:
        target: адрес spiritvpnd в формате host:port.
        client_cert_file: путь к клиентскому сертификату (identity бота).
        client_key_file: путь к приватному ключу клиентского сертификата.
        ca_file: путь к CA, которым подписан серверный сертификат spiritvpnd.

    Returns:
        Стаб CustomerAccessService поверх защищённого канала.
    """
    with open(ca_file, "rb") as f:
        root_certificates = f.read()
    with open(client_cert_file, "rb") as f:
        certificate_chain = f.read()
    with open(client_key_file, "rb") as f:
        private_key = f.read()

    credentials = grpc.ssl_channel_credentials(
        root_certificates=root_certificates,
        private_key=private_key,
        certificate_chain=certificate_chain,
    )
    channel = grpc.aio.secure_channel(target, credentials)
    return CustomerAccessServiceStub(channel)
