import pytest

from pkh.storage.unified import KnowledgeStore


@pytest.fixture
def tmp_data_dir(tmp_path):
    return tmp_path


@pytest.fixture
def knowledge_store(tmp_path):
    store = KnowledgeStore(
        metadata_path=str(tmp_path / "test.db"),
        vector_path=str(tmp_path / "chroma"),
        graph_path=str(tmp_path / "graph.json"),
    )
    return store


@pytest.fixture
def sample_git_repo(tmp_path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    # init git repo
    import subprocess

    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
    # create python file
    (repo / "payment.py").write_text(
        '''
class PaymentService:
    """Handles payment processing."""
    def charge(self, amount: float) -> bool:
        """Charge a payment."""
        return self.validate(amount)

    def validate(self, amount: float) -> bool:
        return amount > 0

def process_payment(amount):
    svc = PaymentService()
    return svc.charge(amount)
'''
    )
    (repo / "README.md").write_text("# Sample\nThis is a payment service.")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True)
    return repo
