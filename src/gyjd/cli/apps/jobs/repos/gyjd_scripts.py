import subprocess
import sys
from pathlib import Path

import toml
from dagster import Field, OpExecutionContext, ScheduleDefinition, Shape, job, op, repository

# Diretório com os arquivos Python
PYTHON_SCRIPTS_DIR = "/Users/mariotaddeucci/Documents/GitHub/python-gyjd/examples"  # os.path.abspath(os.path.join(os.path.dirname(__file__), "examples"))


def run_uv_command(script_uri, *, python_version=None, dependencies=None) -> int:
    command = [sys.executable, "-m", "uv", "run", "--no-project"]

    if python_version:
        command.extend(["--python", python_version])

    if dependencies:
        command.extend(["--with", ",".join(dependencies)])

    command.extend(["--script", str(script_uri)])

    process = subprocess.run(command, stdout=None, stderr=None, text=True)

    return process.returncode


# Op que executará um script Python
@op(config_schema=Shape({"script_path": Field(str, description="Caminho para o script Python")}))
def run_python_script(context: OpExecutionContext):
    script_path = context.op_config["script_path"]
    context.log.info(f"Executando script: {script_path}")

    exit_code = run_uv_command(script_path)

    if exit_code != 0:
        raise Exception(f"Falha ao executar o script: {script_path}")


# Função para criar um job para cada script
def create_job_for_script(script_name: str, script_path: str):
    @job(name=script_name)
    def dynamic_job():
        run_python_script.configured({"script_path": script_path}, name=f"{script_name}_op")()

    return dynamic_job


# Cria um schedule para cada job
def create_schedule_for_job(job):
    return ScheduleDefinition(job=job, cron_schedule="0 6 * * *")


# Gera os jobs e schedules dinamicamente
def generate_jobs_and_schedules():
    jobs = []
    schedules = []

    scripts_path = Path(PYTHON_SCRIPTS_DIR)

    for config_path in scripts_path.glob("**/*.toml"):
        with open(config_path) as f:
            try:
                script_config = toml.load(f)
            except toml.TomlDecodeError:
                continue

        if "script" not in script_config:
            continue

        script_path: Path = config_path.parent / script_config["script"]
        script_name = script_config.get("name", script_path.stem)

        job = create_job_for_script(script_name, str(script_path))
        schedule = create_schedule_for_job(job)

        jobs.append(job)
        schedules.append(schedule)

    return jobs, schedules


# Repositório contendo os jobs e schedules
@repository(
    name="scripts_repository",
    description="Repositório com jobs e schedules para scripts Python em ambientes isolados utilizando uv coordenadamente",
)
def scripts_repository():
    jobs, schedules = generate_jobs_and_schedules()
    return jobs + schedules
