import importlib.util
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INIT_DATABASE_PATH = PROJECT_ROOT / "deploy" / "init_database.py"

spec = importlib.util.spec_from_file_location("init_database", INIT_DATABASE_PATH)
init_database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(init_database)


class DeploymentTests(unittest.TestCase):
    def test_schema_is_not_bound_to_a_database_name(self):
        schema = init_database.read_sql(PROJECT_ROOT / "deploy" / "database" / "CancerRegistry_System.sql")
        self.assertNotRegex(schema, r"(?im)^\s*USE\s+")
        self.assertGreater(len(init_database.load_sql_batches()), 0)

    def test_application_has_separate_development_and_production_modes(self):
        app_source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('APP_ENV = os.environ.get("APP_ENV", "development")', app_source)
        self.assertIn('if APP_ENV == "production":', app_source)
        self.assertIn('serve(app, host=waitress_host', app_source)
        self.assertIn('app.run(host=flask_host, port=flask_port, debug=APP_DEBUG)', app_source)
        self.assertIn('@app.get("/health")', app_source)

    def test_deployment_scripts_cover_first_and_later_deployments(self):
        setup_script = (PROJECT_ROOT / "deploy" / "setup-and-deploy.ps1").read_text(encoding="utf-8")
        deploy_script = (PROJECT_ROOT / "deploy" / "deploy-production.ps1").read_text(encoding="utf-8")
        iis_script = (PROJECT_ROOT / "deploy" / "configure-iis.ps1").read_text(encoding="utf-8")
        self.assertIn("-InitializeDatabase", setup_script)
        self.assertIn("[switch]$InitializeDatabase", deploy_script)
        self.assertIn("CancerRegistryBackend", iis_script)
        self.assertIn("clientCache", iis_script)


if __name__ == "__main__":
    unittest.main()