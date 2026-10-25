"""Servidor web do ImóvelPro, usando o mesmo SQLite da versão desktop."""

from __future__ import annotations

import csv
import io
import os
from datetime import date, timedelta
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import dao
from database import get_conn, init_db

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

@asynccontextmanager
async def lifespan(_app):
    init_db()
    yield


app = FastAPI(
    title="ImóvelPro Web", docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")


def _row(row):
    return dict(row) if row is not None else None


def _error(message, status=400):
    raise HTTPException(status_code=status, detail=message)


def _result(result):
    ok, message = result
    if not ok:
        _error(message)
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


def _bootstrap_data():
    clientes = []
    for item in dao.listar_clientes():
        row, phones = dao.get_cliente(item["id"])
        obj = _row(row)
        obj["telefones"] = phones
        clientes.append(obj)

    corretores = []
    for item in dao.listar_corretores():
        row, phones = dao.get_corretor(item["id"])
        obj = _row(row)
        obj["telefones"] = phones
        corretores.append(obj)

    imoveis = []
    for item in dao.listar_imoveis():
        row, owners = dao.get_imovel(item["id"])
        obj = _row(row)
        obj["proprietarios"] = [
            {"clienteId": owner["cliente_id"], "pct": owner["percentual"]}
            for owner in owners]
        obj["venda"] = obj.pop("preco_venda")
        obj["aluguel"] = obj.pop("preco_aluguel")
        imoveis.append(obj)

    contratos = []
    for item in dao.listar_contratos():
        row, buyers, sellers, brokers = dao.get_contrato(item["id"])
        obj = _row(row)
        obj.update({
            "data": obj.pop("data_assinatura"),
            "imovelId": obj.pop("imovel_id"),
            "entrada": obj.pop("valor_entrada"),
            "parcelas": obj.pop("num_parcelas"),
            "duracao": obj.pop("duracao_meses"),
            "vencdia": obj.pop("dia_vencimento"),
            "adquirentes": [
                {"clienteId": value["cliente_id"]} for value in buyers],
            "cedentes": [
                {"clienteId": value["cliente_id"]} for value in sellers],
            "corretores": [
                {"corretorId": value["corretor_id"],
                 "pct": value["percentual"]} for value in brokers],
        })
        contratos.append(obj)

    boletos = []
    for item in dao.listar_boletos():
        obj = _row(item)
        boletos.append({
            "id": obj["id"], "seq": obj["sequencial"],
            "contratoId": obj["contrato_id"], "tipo": obj["tipo"],
            "situacao": obj["situacao"], "valor": obj["valor"],
            "vencimento": obj["data_vencimento"],
            "pagamento": obj["data_pagamento"],
        })

    conn = get_conn()
    next_ids = {}
    for plural, table in (
            ("clientes", "cliente"), ("corretores", "corretor"),
            ("imoveis", "imovel"), ("contratos", "contrato"),
            ("boletos", "boleto")):
        next_ids[plural] = conn.execute(
            f"SELECT COALESCE(MAX(id), 0) + 1 FROM {table}").fetchone()[0]
    conn.close()
    return {
        "clientes": clientes, "corretores": corretores,
        "imoveis": imoveis, "contratos": contratos,
        "boletos": boletos, "nextIds": next_ids,
    }


@app.get("/api/bootstrap")
def bootstrap():
    return _bootstrap_data()


@app.get("/api/reports/operations")
def operations_report(period: int = 30, city: str = ""):
    period = max(1, min(period, 365))
    conn = get_conn()
    try:
        _today = date.today()
        deadline = (_today + timedelta(days=period)).isoformat()
        city_filter = " AND lower(im.cidade)=lower(?)" if city.strip() else ""
        params = [city.strip()] if city.strip() else []
        available = conn.execute(
            "SELECT COUNT(*) FROM imovel im WHERE im.status='disponivel'"
            + city_filter, params).fetchone()[0]
        inventory = conn.execute(
            "SELECT COUNT(*) AS quantidade, im.cidade, "
            "COALESCE(SUM(COALESCE(im.preco_venda, im.preco_aluguel)),0) AS valor "
            "FROM imovel im WHERE im.status='disponivel'" + city_filter +
            " GROUP BY im.cidade ORDER BY quantidade DESC, im.cidade",
            params).fetchall()
        expiring = conn.execute(
            "SELECT ct.id, ct.codigo, ct.tipo, ct.situacao, ct.data_assinatura, "
            "ct.duracao_meses, im.codigo AS imovel_codigo, im.cidade, im.bairro, "
            "date(ct.data_assinatura, '+' || ct.duracao_meses || ' months') AS fim "
            "FROM contrato ct JOIN imovel im ON im.id=ct.imovel_id "
            "WHERE ct.situacao='ativo' AND ct.duracao_meses IS NOT NULL "
            "AND date(ct.data_assinatura, '+' || ct.duracao_meses || ' months') "
            "BETWEEN ? AND ? ORDER BY fim LIMIT 50",
            (_today.isoformat(), deadline)).fetchall()
        bills = conn.execute(
            "SELECT COUNT(*) AS quantidade, COALESCE(SUM(valor),0) AS valor "
            "FROM boleto WHERE situacao='vencido'").fetchone()
        return {
            "period": period,
            "summary": {"disponiveis": available,
                        "contratosAVencer": len(expiring),
                        "boletosVencidos": bills["quantidade"],
                        "valorBoletosVencidos": bills["valor"]},
            "inventoryByCity": [dict(row) for row in inventory],
            "expiringContracts": [dict(row) for row in expiring],
        }
    finally:
        conn.close()


@app.get("/api/reports/operations.csv")
def operations_report_csv(period: int = 30, city: str = ""):
    report = operations_report(period, city)
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Relatório operacional ImóvelPro"])
    writer.writerow(["Período de contratos a vencer (dias)", report["period"]])
    writer.writerow(["Imóveis disponíveis", report["summary"]["disponiveis"]])
    writer.writerow(["Boletos vencidos", report["summary"]["boletosVencidos"]])
    writer.writerow(["Valor de boletos vencidos", report["summary"]["valorBoletosVencidos"]])
    writer.writerow([])
    writer.writerow(["Estoque disponível por cidade", "Quantidade", "Valor anunciado (aprox.)"])
    for item in report["inventoryByCity"]:
        writer.writerow([item["cidade"], item["quantidade"], item["valor"]])
    writer.writerow([])
    writer.writerow(["Contratos a vencer", "Tipo", "Imóvel", "Endereço", "Data final"])
    for item in report["expiringContracts"]:
        writer.writerow([item["codigo"], item["tipo"], item["imovel_codigo"],
                         f"{item['bairro']}, {item['cidade']}", item["fim"]])
    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=relatorio-operacional-imovelpro.csv"})


@app.post("/api/clientes")
def create_cliente(payload: dict):
    data = {key: payload.get(key) for key in ("codigo", "nome", "cpf", "perfil")}
    _result(dao.salvar_cliente(data, payload.get("telefones") or []))
    return {"ok": True}


@app.put("/api/clientes/{item_id}")
def update_cliente(item_id: int, payload: dict):
    data = {key: payload.get(key) for key in ("codigo", "nome", "cpf", "perfil")}
    _result(dao.salvar_cliente(
        data, payload.get("telefones") or [], item_id))
    return {"ok": True}


@app.delete("/api/clientes/{item_id}")
def delete_cliente(item_id: int):
    return _result(dao.excluir_cliente(item_id))


@app.post("/api/corretores")
def create_corretor(payload: dict):
    data = {key: payload.get(key) for key in ("nome", "cpf", "creci")}
    return _result(dao.salvar_corretor(data, payload.get("telefones") or []))


@app.put("/api/corretores/{item_id}")
def update_corretor(item_id: int, payload: dict):
    data = {key: payload.get(key) for key in ("nome", "cpf", "creci")}
    return _result(dao.salvar_corretor(
        data, payload.get("telefones") or [], item_id))


@app.delete("/api/corretores/{item_id}")
def delete_corretor(item_id: int):
    return _result(dao.excluir_corretor(item_id))


def _imovel_payload(payload):
    return {
        "codigo": payload.get("codigo"), "categoria": payload.get("categoria"),
        "subtipo": payload.get("subtipo"), "area": payload.get("area"),
        "rua": payload.get("rua"), "numero": payload.get("numero"),
        "bairro": payload.get("bairro"), "cidade": payload.get("cidade"),
        "finalidade": payload.get("finalidade"),
        "preco_venda": payload.get("venda"),
        "preco_aluguel": payload.get("aluguel"),
    }, [
        {"cliente_id": value.get("clienteId"), "percentual": value.get("pct")}
        for value in payload.get("proprietarios") or []]


@app.post("/api/imoveis")
def create_imovel(payload: dict):
    data, owners = _imovel_payload(payload)
    return _result(dao.salvar_imovel(data, owners))


@app.put("/api/imoveis/{item_id}")
def update_imovel(item_id: int, payload: dict):
    data, owners = _imovel_payload(payload)
    return _result(dao.salvar_imovel(data, owners, item_id))


@app.delete("/api/imoveis/{item_id}")
def delete_imovel(item_id: int):
    return _result(dao.excluir_imovel(item_id))


def _contrato_payload(payload):
    data = {
        "codigo": payload.get("codigo"), "tipo": payload.get("tipo"),
        "valor": payload.get("valor"), "comissao": payload.get("comissao"),
        "data_assinatura": payload.get("data"),
        "situacao": payload.get("situacao"),
        "imovel_id": payload.get("imovelId"),
        "valor_entrada": payload.get("entrada"),
        "num_parcelas": payload.get("parcelas"),
        "duracao_meses": payload.get("duracao"),
        "dia_vencimento": payload.get("vencdia"),
    }
    buyers = [v.get("clienteId") for v in payload.get("adquirentes") or []]
    sellers = [v.get("clienteId") for v in payload.get("cedentes") or []]
    brokers = [
        {"corretor_id": v.get("corretorId"), "percentual": v.get("pct")}
        for v in payload.get("corretores") or []]
    return data, buyers, sellers, brokers


@app.post("/api/contratos")
def create_contrato(payload: dict):
    data, buyers, sellers, brokers = _contrato_payload(payload)
    result = dao.salvar_contrato(data, buyers, sellers, brokers)
    if result[0]:
        conn = get_conn()
        contract_id = conn.execute(
            "SELECT id FROM contrato WHERE codigo=?",
            (data["codigo"],)).fetchone()[0]
        conn.close()
        dao.gerar_boletos_contrato(contract_id)
    return _result(result)


@app.put("/api/contratos/{item_id}")
def update_contrato(item_id: int, payload: dict):
    data, buyers, sellers, brokers = _contrato_payload(payload)
    result = dao.salvar_contrato(data, buyers, sellers, brokers, item_id)
    if result[0]:
        dao.gerar_boletos_contrato(item_id)
    return _result(result)


@app.delete("/api/contratos/{item_id}")
def delete_contrato(item_id: int):
    return _result(dao.excluir_contrato(item_id))


def _boleto_payload(payload):
    return {
        "sequencial": payload.get("seq"),
        "contrato_id": payload.get("contratoId"),
        "tipo": payload.get("tipo"), "situacao": payload.get("situacao"),
        "valor": payload.get("valor"),
        "data_vencimento": payload.get("vencimento"),
        "data_pagamento": payload.get("pagamento"),
    }


@app.post("/api/boletos")
def create_boleto(payload: dict):
    if not payload.get("seq"):
        payload["seq"] = dao.proximo_sequencial_boleto()
    return _result(dao.salvar_boleto(_boleto_payload(payload)))


@app.put("/api/boletos/{item_id}")
def update_boleto(item_id: int, payload: dict):
    return _result(dao.salvar_boleto(_boleto_payload(payload), item_id))


@app.delete("/api/boletos/{item_id}")
def delete_boleto(item_id: int):
    return _result(dao.excluir_boleto(item_id))


def run():
    import uvicorn
    host = os.getenv("IMOVELPRO_WEB_HOST", "127.0.0.1")
    port = int(os.getenv("IMOVELPRO_WEB_PORT", "8000"))
    uvicorn.run("web_app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()


