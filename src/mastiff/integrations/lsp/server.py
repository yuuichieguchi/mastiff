"""Minimal LSP server for mastiff using pygls."""

from __future__ import annotations

from lsprotocol.types import TEXT_DOCUMENT_DID_SAVE, DidSaveTextDocumentParams
from pygls.server import LanguageServer

server = LanguageServer("mastiff", "v0.1.0")


@server.feature(TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: LanguageServer, params: DidSaveTextDocumentParams) -> None:
    """Trigger review on file save."""
    ls.show_message_log(f"File saved: {params.text_document.uri}")


def start_server() -> None:
    """Start the LSP server in stdio mode."""
    server.start_io()
