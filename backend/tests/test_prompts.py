from backend.cli import escolher_relato, montar_prompt
from backend.domain.models import PerfilCliente, Ticket


def test_prompt_preenche_perfil_e_relato():
    perfil = PerfilCliente("0004", "Marcos", "avancado", "didatico", "email")
    prompt = montar_prompt(perfil, "O arquivo não aparece na pasta.")
    assert "Marcos (ID 0004)" in prompt
    assert "Nível: avancado. Estilo: didatico. Canal: email." in prompt
    assert "O arquivo não aparece na pasta." in prompt
    assert "sinal_esperado" in prompt


def test_escolhe_ticket_do_catalogo(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "pasta")
    ticket = Ticket("pasta", "Pasta compartilhada", "O arquivo não aparece.")
    assert escolher_relato([ticket]) == ticket.descricao
