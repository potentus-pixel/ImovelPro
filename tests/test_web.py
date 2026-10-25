import os
import tempfile
import unittest

from fastapi.testclient import TestClient

import database
import web_app


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.old_path = database.DB_PATH
        database.DB_PATH = os.path.join(self.tempdir.name, "web.db")
        database.init_db()
        self.client = TestClient(web_app.app)

    def tearDown(self):
        self.client.close()
        database.DB_PATH = self.old_path
        self.tempdir.cleanup()

    def test_page_and_data_are_available_without_authentication(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ImóvelPro", response.text)
        self.assertEqual(self.client.get("/api/bootstrap").status_code, 200)

    def test_bootstrap_returns_data_without_authentication(self):
        response = self.client.get("/api/bootstrap")
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertGreater(len(data["clientes"]), 0)
        self.assertIn("nextIds", data)

    def test_web_write_is_visible_in_shared_database(self):
        response = self.client.post("/api/clientes", json={
            "codigo": "CLI-WEB", "nome": "Cliente da Web",
            "cpf": "999.888.777-66", "perfil": "interessado",
            "telefones": ["(21) 99999-0000"]})
        self.assertEqual(response.status_code, 200, response.text)

        conn = database.get_conn()
        row = conn.execute(
            "SELECT nome FROM cliente WHERE codigo='CLI-WEB'").fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["nome"], "Cliente da Web")

    def test_all_business_modules_support_web_crud(self):

        response = self.client.post("/api/corretores", json={
            "nome": "Corretor Web", "cpf": "888.777.666-55",
            "creci": "WEB/RJ", "telefones": ["(21) 90000-0001"]})
        self.assertEqual(response.status_code, 200, response.text)
        data = self.client.get("/api/bootstrap").json()
        broker = next(c for c in data["corretores"] if c["creci"] == "WEB/RJ")
        response = self.client.put(f"/api/corretores/{broker['id']}", json={
            **broker, "nome": "Corretor Web Atualizado"})
        self.assertEqual(response.status_code, 200, response.text)

        response = self.client.post("/api/imoveis", json={
            "codigo": "IM-WEB", "categoria": "Urbano", "subtipo": "Casa",
            "area": 90, "rua": "Rua Web", "numero": "10",
            "bairro": "Centro", "cidade": "Niterói", "finalidade": "venda",
            "venda": 350000, "aluguel": None,
            "proprietarios": [{"clienteId": 1, "pct": 100}]})
        self.assertEqual(response.status_code, 200, response.text)
        data = self.client.get("/api/bootstrap").json()
        property_ = next(i for i in data["imoveis"] if i["codigo"] == "IM-WEB")
        response = self.client.put(f"/api/imoveis/{property_['id']}", json={
            **property_, "bairro": "Icaraí"})
        self.assertEqual(response.status_code, 200, response.text)

        response = self.client.post("/api/contratos", json={
            "codigo": "CT-WEB", "tipo": "venda", "valor": 350000,
            "comissao": 10000, "data": "2026-07-30", "situacao": "em espera",
            "imovelId": property_["id"], "entrada": 50000, "parcelas": 0,
            "adquirentes": [{"clienteId": 2}],
            "cedentes": [{"clienteId": 1}],
            "corretores": [{"corretorId": broker["id"], "pct": 100}]})
        self.assertEqual(response.status_code, 200, response.text)
        data = self.client.get("/api/bootstrap").json()
        contract = next(c for c in data["contratos"] if c["codigo"] == "CT-WEB")
        response = self.client.put(f"/api/contratos/{contract['id']}", json={
            **contract, "situacao": "ativo"})
        self.assertEqual(response.status_code, 200, response.text)

        response = self.client.post("/api/boletos", json={
            "seq": "BOL-WEB", "contratoId": contract["id"],
            "tipo": "comissao", "situacao": "pendente", "valor": 500,
            "vencimento": "2030-01-01", "pagamento": None})
        self.assertEqual(response.status_code, 200, response.text)
        data = self.client.get("/api/bootstrap").json()
        bill = next(b for b in data["boletos"] if b["seq"] == "BOL-WEB")
        response = self.client.put(f"/api/boletos/{bill['id']}", json={
            **bill, "pagamento": "2026-07-30"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            next(b for b in self.client.get("/api/bootstrap").json()["boletos"]
                 if b["id"] == bill["id"])["situacao"], "pago")

        self.assertEqual(
            self.client.delete(f"/api/boletos/{bill['id']}").status_code, 200)
        self.assertEqual(
            self.client.delete(f"/api/contratos/{contract['id']}").status_code,
            200)
        self.assertEqual(
            self.client.delete(f"/api/imoveis/{property_['id']}").status_code,
            200)
        self.assertEqual(
            self.client.delete(f"/api/corretores/{broker['id']}").status_code,
            200)

    def test_operational_report_and_csv_download(self):
        report = self.client.get("/api/reports/operations?period=60")
        self.assertEqual(report.status_code, 200, report.text)
        data = report.json()
        self.assertEqual(data["period"], 60)
        self.assertIn("disponiveis", data["summary"])
        self.assertTrue(data["inventoryByCity"])

        filtered = self.client.get(
            "/api/reports/operations?period=30&city=Itaperuna").json()
        self.assertEqual(len(filtered["inventoryByCity"]), 1)
        self.assertEqual(filtered["inventoryByCity"][0]["cidade"], "Itaperuna")

        exported = self.client.get("/api/reports/operations.csv?period=30")
        self.assertEqual(exported.status_code, 200)
        self.assertIn("text/csv", exported.headers["content-type"])
        self.assertIn("Estoque disponível por cidade", exported.text)


if __name__ == "__main__":
    unittest.main()





