from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    cassandra_hosts: str = "localhost"
    cassandra_keyspace: str = "financial_dw"
    cassandra_port: int = 9042
    cassandra_dc: str = "datacenter1"
    cassandra_replication_strategy: str = "SimpleStrategy"
    cassandra_replication_factor: int = 1
    nasdaq_api_key: str = "https://data.nasdaq.com/api/v3/datatables"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    ollama_base_ur: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    model_config = {"env_file": ".env"}

    @property
    def cassandra_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.cassandra_hosts.split(",")]
    
settings = Settings()