from pathlib import Path
import tempfile

from openpilot.common.params import Params
from openpilot.system.athena.registration import register, UNREGISTERED_DONGLE_ID
from openpilot.system.hardware.hw import Paths


class TestRegistration:
  def setup_method(self):
    self.params = Params()
    self.serial = "cccccccc"

    persist_dir = Path(Paths.persist_root()) / "comma"
    persist_dir.mkdir(parents=True, exist_ok=True)
    self.tempdir = Path(tempfile.mkdtemp(prefix="op_auth_test_"))
    self.cache_file = self.tempdir / "activation_authorized_serial"
    if self.cache_file.exists():
      self.cache_file.unlink()

  def teardown_method(self):
    self.params.remove("DongleId")
    if self.cache_file.exists():
      self.cache_file.unlink()
    if self.tempdir.exists():
      self.tempdir.rmdir()

  def test_whitelist_bypass(self, mocker):
    mocker.patch("openpilot.system.athena.registration.HARDWARE.get_serial", return_value=self.serial)
    mocker.patch("openpilot.system.athena.registration.ACTIVATION_CACHE_FILE", self.cache_file)
    dongle = register()
    assert dongle != UNREGISTERED_DONGLE_ID
    assert self.params.get("DongleId") == dongle

  def test_cached_authorization(self, mocker):
    mocker.patch("openpilot.system.athena.registration.HARDWARE.get_serial", return_value="nonwhite")
    mocker.patch("openpilot.system.athena.registration.ACTIVATION_CACHE_FILE", self.cache_file)
    self.cache_file.parent.mkdir(parents=True, exist_ok=True)
    self.cache_file.write_text("nonwhite\n")
    dongle = register()
    assert dongle != UNREGISTERED_DONGLE_ID
    assert self.params.get("DongleId") == dongle

  def test_server_authorized(self, mocker):
    mocker.patch("openpilot.system.athena.registration.HARDWARE.get_serial", return_value="srv-ok")
    mocker.patch("openpilot.system.athena.registration.ACTIVATION_CACHE_FILE", self.cache_file)
    mock_resp = mocker.Mock()
    mock_resp.json.return_value = {"license_status": "authorized"}
    mock_resp.raise_for_status.return_value = None
    mocker.patch("openpilot.system.athena.registration.requests.post", return_value=mock_resp)
    dongle = register()
    assert dongle != UNREGISTERED_DONGLE_ID
    assert self.params.get("DongleId") == dongle
    assert self.cache_file.read_text().strip() == "srv-ok"

  def test_server_unregistered_without_lock(self, mocker):
    mocker.patch("openpilot.system.athena.registration.HARDWARE.get_serial", return_value="srv-no")
    mocker.patch("openpilot.system.athena.registration.ACTIVATION_CACHE_FILE", self.cache_file)
    mock_resp = mocker.Mock()
    mock_resp.json.return_value = {"license_status": "blocked"}
    mock_resp.raise_for_status.return_value = None
    mocker.patch("openpilot.system.athena.registration.requests.post", return_value=mock_resp)
    mocker.patch("openpilot.system.athena.registration.ACTIVATION_LOCK_UNREGISTERED", False)
    dongle = register()
    assert dongle == UNREGISTERED_DONGLE_ID
    assert self.params.get("DongleId") == UNREGISTERED_DONGLE_ID
