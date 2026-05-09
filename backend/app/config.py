from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    cassandra_hosts: str = "localhost"
    cassandra_keyspace: str = "financial_dw"
    cassandra_port: int = 9042
    cassandra_dc: str = "datacenter1"
    cassandra_replication_strategy: str = "SimpleStrategy"
    cassandra_replication_factor: int = 1
    nasdaq_api_key: str = ""
    rabbitmq_url: str = ""
    ollama_base_ur: str = ""
    ollama_model: str = ""

    model_config = {"env_file": ".env"}

    @property
    def cassandra_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.cassandra_hosts.split(",")]
    
settings = Settings()