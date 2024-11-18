import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import toml
from dagster import Field, OpExecutionContext, ScheduleDefinition, Shape, job, op, repository


@dataclass
class ScriptConfig:
    script_path: str
    script_name: str
    python_version: str
    dependencies: list[str] = field(default_factory=list)


@op(
    config_schema=Shape(
        {
            "script_path": Field(str, description="Caminho para o script Python"),
            "python_version": Field(str, description="Versão do Python"),
            "dependencies": Field([str], description="Dependências do script"),
        }
    )
)
def run_python_script(context: OpExecutionContext):
    script_path = context.op_config["script_path"]
    python_version = context.op_config["python_version"]
    dependencies = context.op_config["dependencies"]

    context.log.info(f"Starting script: {script_path}")

    command = [sys.executable, "-m", "uv", "run", "--no-project"]

    if python_version:
        command.extend(["--python", python_version])

    if dependencies:
        command.extend(["--with", ",".join(dependencies)])

    command.extend(["--script", str(script_path)])

    envs = os.environ.copy()

    logger_prefix = "gyjd-jobs -"

    envs["LOG_FORMATTER"] = f"{logger_prefix} - %(levelname)s - %(message)s"

    process = subprocess.Popen(command, stdout=None, stderr=None, text=True, env=envs)

    exit_code = process.wait()
    if exit_code != 0:
        raise Exception(f"Script finished with exit code: {exit_code}")

    context.log.info(f"Script finished with exit code: {exit_code}")


# Função para criar um job para cada script
def create_job_for_script(config: ScriptConfig):
    @job(name=config.script_name)
    def dynamic_job():
        run_python_script.configured(
            {
                "script_path": config.script_path,
                "python_version": config.python_version,
                "dependencies": config.dependencies,
            },
            name=f"{config.script_name}_op",
        )()

    return dynamic_job


def generate_definitions(scripts_path: Path):
    for config_path in scripts_path.glob("**/*.toml"):
        with open(config_path) as f:
            try:
                script_config = toml.load(f).get("gyjd", {}).get("job", {})
            except toml.TomlDecodeError:
                continue

        if "script" not in script_config:
            continue

        script_path = (scripts_path / config_path).parent / script_config["script"]

        config = ScriptConfig(
            script_path=str(script_path),
            script_name=script_config.get("name", script_path.stem),
            python_version=script_config.get("python_version", f"{sys.version_info.major}.{sys.version_info.minor}"),
            dependencies=script_config.get("dependencies", []),
        )

        job = create_job_for_script(config=config)

        yield job

        schedules = script_config.get("schedule", {})

        for schedule_name, schedule_config in schedules.get("cron", {}).items():
            cron_expression = schedule_config.get("expression")
            if not cron_expression:
                continue

            cron_timezone = schedule_config.get("timezone", "UTC")

            yield ScheduleDefinition(
                job=job,
                cron_schedule=cron_expression,
                execution_timezone=cron_timezone,
                name=f"{config.script_name}_{schedule_name}_schedule",
            )


@repository(
    name="scripts_repository",
    description="Repositório com jobs e schedules para scripts Python em ambientes isolados utilizando uv coordenadamente",
)
def scripts_repository():
    scripts_path = Path(os.environ["GYJD_SCRIPTS_PATH"])
    return list(generate_definitions(scripts_path=scripts_path))
