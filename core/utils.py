import datetime
import locale

def formatar_dinheiro(valor: float) -> str:
    """Formata um valor de floater para string monetária brasileira R$ 1.234,56."""
    try:
        # Use simple manual formatting to remain environment-independent of local-locale settings
        v_str = f"{abs(valor):,.2f}"
        v_str = v_str.replace(",", "X").replace(".", ",").replace("X", ".")
        prefix = "-" if valor < 0 else ""
        return f"{prefix}R$ {v_str}"
    except Exception:
        return f"R$ {valor:.2f}"

def formatar_data_br(data_iso: str) -> str:
    """Converte datas do formato YYYY-MM-DD para DD/MM/AAAA."""
    if not data_iso:
        return ""
    try:
        # If timestamp is passed, parse only date portion
        if " " in data_iso:
            data_iso = data_iso.split(" ")[0]
        elif "T" in data_iso:
            data_iso = data_iso.split("T")[0]
        partes = data_iso.split("-")
        if len(partes) == 3:
            return f"{partes[2]}/{partes[1]}/{partes[0]}"
        return data_iso
    except Exception:
        return data_iso

def converter_data_iso(data_br: str) -> str:
    """Converte datas do formato DD/MM/AAAA para YYYY-MM-DD."""
    if not data_br:
        return ""
    try:
        partes = data_br.split("/")
        if len(partes) == 3:
            return f"{partes[2]}-{partes[1]}-{partes[0]}"
        return data_br
    except Exception:
        return data_br

def extrair_mes_ano_extenso(mes_ano_str: str) -> str:
    """Converte e.g. 2026-06 para Junho de 2026."""
    if not mes_ano_str or "-" not in mes_ano_str:
        return mes_ano_str
    try:
        ano, mes = mes_ano_str.split("-")[:2]
        meses = {
            "01": "Janeiro",
            "02": "Fevereiro",
            "03": "Março",
            "04": "Abril",
            "05": "Maio",
            "06": "Junho",
            "07": "Julho",
            "08": "Agosto",
            "09": "Setembro",
            "10": "Outubro",
            "11": "Novembro",
            "12": "Dezembro"
        }
        return f"{meses.get(mes, 'Mês')} de {ano}"
    except Exception:
        return mes_ano_str
