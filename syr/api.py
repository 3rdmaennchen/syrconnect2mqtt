#1 Project/ 1 Device

import requests
import datetime
import xmltodict
from typing import Any, Dict, List, Optional

from .crypto import SYRCrypto
from .checksum import SYRChecksum


class SYRApiError(Exception):
    pass


class SYRClient:
    BASE_API = "https://syrconnect.de/WebServices/Api/SyrApiService.svc/REST"
    BASE_CTRL = "https://syrconnect.de/WebServices/SyrControlWebServiceTest2.asmx"

    def __init__(self, username: str, password: str, logger=None) -> None:
        self.username = username
        self.password = password
        self.logger = logger
        self.session_id: Optional[str] = None
        self.checksum = SYRChecksum(
            "L8KZG4F5DSM6ANBV3CXY7W2ER1T9H0UP",
            "KHGK5X29LVNZU56T",
        )

    def _log_debug(self, msg: str) -> None:
        if self.logger:
            self.logger.debug(msg)

    def _log_info(self, msg: str) -> None:
        if self.logger:
            self.logger.info(msg)

    def _log_error(self, msg: str) -> None:
        if self.logger:
            self.logger.error(msg)

    def login_and_get_projects(self) -> List[Dict[str, Any]]:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload_inner = (
            f'<nfo v="SYR Connect" version="3.7.10" osv="15.8.3" os="iOS" '
            f'dn="iPhone" ts="{ts}" tzo="01:00:00" lng="de" reg="DE" />'
            f'<usr n="{self.username}" v="{self.password}" />'
        )
        xml_payload = f'<?xml version="1.0" encoding="utf-8"?><sc><api version="1.0">{payload_inner}</api></sc>'

        self._log_debug(f"Login XML: {xml_payload}")
        res = requests.post(
            f"{self.BASE_API}/GetProjects",
            data=xml_payload,
            headers={
                "Content-Type": "text/xml",
                "Connection": "keep-alive",
                "Accept": "*/*",
                "User-Agent": "SYR/400 CFNetwork/1335.0.3.4 Darwin/21.6.0",
                "Accept-Language": "de-DE,de;q=0.9",
            },
            timeout=30,
        )

        if res.status_code != 200:
            raise SYRApiError(f"GetProjects HTTP {res.status_code}: {res.text}")

        self._log_debug(f"GetProjects raw response: {res.text}")

        outer = xmltodict.parse(res.text)
        encrypted_text = outer["sc"]["api"]["_text"]
        decrypted = SYRCrypto.decrypt_base64(encrypted_text)
        self._log_debug(f"Decrypted projects XML: {decrypted}")

        inner = xmltodict.parse(f"<xml>{decrypted}</xml>")
        self._log_debug(f"Parsed projects JSON: {inner}")

        usr = inner["xml"]["usr"]
        self.session_id = usr.get("@id") or usr.get("id")

        prs = inner["xml"]["prs"]["pre"]
        if not isinstance(prs, list):
            prs = [prs]

        projects: List[Dict[str, Any]] = []
        for pr in prs:
            pid = pr.get("@id") or pr.get("id")
            name = pr.get("@n") or pr.get("n") or pid
            projects.append({"id": pid, "name": name})

        self._log_info(f"Found {len(projects)} projects")
        return projects

    def get_devices_for_project(self, project_id: str) -> List[Dict[str, Any]]:
        payload = (
            f'<?xml version="1.0" encoding="utf-8"?><sc>'
            f'<si v="App-3.7.10-de-DE-iOS-iPhone-15.8.3-de.consoft.syr.connect" />'
            f'<us ug="{self.session_id}" />'
            f'<prs><pr pg="{project_id}" /></prs>'
            f'</sc>'
        )

        self.checksum.reset_checksum()
        self.checksum.add_xml_to_checksum(payload)
        cs = self.checksum.get_checksum()
        payload_with_cs = payload.replace("</sc>", f'<cs v="{cs}"/></sc>')

        self._log_debug(f"GetProjectDeviceCollections XML: {payload_with_cs}")

        res = requests.post(
            f"{self.BASE_CTRL}/GetProjectDeviceCollections",
            data={"xml": payload_with_cs},
            headers={
                "Host": "syrconnect.de",
                "Content-Type": "application/x-www-form-urlencoded",
                "Connection": "keep-alive",
                "Accept": "*/*",
                "User-Agent": "SYR/400 CFNetwork/1335.0.3.4 Darwin/21.6.0",
                "Accept-Language": "de-DE,de;q=0.9",
            },
            timeout=30,
        )

        if res.status_code != 200:
            raise SYRApiError(f"GetProjectDeviceCollections HTTP {res.status_code}: {res.text}")

        self._log_debug(f"GetProjectDeviceCollections raw: {res.text}")
        data = xmltodict.parse(res.text)
        sc = data.get("sc", {})
        dvs = sc.get("dvs")

        device_list: List[Dict[str, Any]] = []
        if dvs is None:
            self._log_error("No devices found in API response")
            return device_list

        if isinstance(dvs, dict) and "d" in dvs:
            devs = dvs["d"]
            if not isinstance(devs, list):
                devs = [devs]
        elif isinstance(dvs, list):
            devs = dvs
        else:
            devs = [dvs]

        for dev in devs:
            dclg = dev.get("@dclg") or dev.get("dclg")
            name = dev.get("@dfw") or dev.get("dfw") or dclg
            device_list.append(
                {"id": dclg, "name": name, "project_id": project_id}
            )

        self._log_info(f"Found {len(device_list)} devices in project {project_id}")
        return device_list

    def get_device_status(self, project_id: str, device_id: str) -> Dict[str, Any]:
        payload = (
            f'<?xml version="1.0" encoding="utf-8"?><sc>'
            f'<si v="App-3.7.10-de-DE-iOS-iPhone-15.8.3-de.consoft.syr.connect" />'
            f'<us ug="{self.session_id}" />'
            f'<col><dcl dclg="{device_id}" fref="1" /></col>'
            f'</sc>'
        )
        self.checksum.reset_checksum()
        self.checksum.add_xml_to_checksum(payload)
        cs = self.checksum.get_checksum()
        payload_with_cs = payload.replace("</sc>", f'<cs v="{cs}"/></sc>')

        self._log_debug(f"GetDeviceCollectionStatus XML: {payload_with_cs}")

        res = requests.post(
            f"{self.BASE_CTRL}/GetDeviceCollectionStatus",
            data={"xml": payload_with_cs},
            headers={
                "Host": "syrconnect.de",
                "Content-Type": "application/x-www-form-urlencoded",
                "Connection": "keep-alive",
                "Accept": "*/*",
                "User-Agent": "SYR/400 CFNetwork/1335.0.3.4 Darwin/21.6.0",
                "Accept-Language": "de-DE,de;q=0.9",
            },
            timeout=30,
        )

        if res.status_code != 200:
            raise SYRApiError(f"GetDeviceCollectionStatus HTTP {res.status_code}: {res.text}")

        self._log_debug(f"GetDeviceCollectionStatus raw: {res.text}")

        data = xmltodict.parse(res.text)
        sc = data.get("sc", {})
        if "msg" in sc:
            self._log_error(f"Error from API: {sc['msg']}")
            return {}

        self._flatten_attributes(sc)
        return sc

    def get_statistics(self, project_id: str, device_id: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        statistic_payloads = [
            {"name": "Salz", "inner": '<sh t="2" rtyp="1" lg="de" rg="DE" unit="kg" />'},
            {"name": "Wasser", "inner": '<sh t="1" rtyp="1" lg="de" rg="DE" unit="l" />'},
        ]

        for stat in statistic_payloads:
            payload = (
                f'<?xml version="1.0" encoding="utf-8"?><sc>'
                f'<si v="App-3.7.10-de-DE-iOS-iPhone-15.8.3-de.consoft.syr.connect" />'
                f'<us ug="{self.session_id}" />'
                f'<col><dcl dclg="{device_id}">{stat["inner"]}</dcl></col>'
                f'</sc>'
            )
            self.checksum.reset_checksum()
            self.checksum.add_xml_to_checksum(payload)
            cs = self.checksum.get_checksum()
            payload_with_cs = payload.replace("</sc>", f'<cs v="{cs}"/></sc>')

            self._log_debug(f"GetLexPlusStatistics XML ({stat['name']}): {payload_with_cs}")

            res = requests.post(
                f"{self.BASE_CTRL}/GetLexPlusStatistics",
                data={"xml": payload_with_cs},
                headers={
                    "Host": "syrconnect.de",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Connection": "keep-alive",
                    "Accept": "*/*",
                    "User-Agent": "SYR/400 CFNetwork/1335.0.3.4 Darwin/21.6.0",
                    "Accept-Language": "de-DE,de;q=0.9",
                },
                timeout=30,
            )

            if res.status_code != 200:
                self._log_error(f"GetLexPlusStatistics HTTP {res.status_code}: {res.text}")
                continue

            self._log_debug(f"GetLexPlusStatistics raw ({stat['name']}): {res.text}")

            data = xmltodict.parse(res.text)
            sc = data.get("sc")
            if not sc:
                self._log_debug(f"No statistics found for {stat['name']}")
                continue
            if "msg" in sc:
                self._log_error(f"Statistics error {stat['name']}: {sc['msg']}")
                continue

            self._flatten_attributes(sc)
            result[stat["name"]] = sc

        return result

    def _flatten_attributes(self, node: Any) -> None:
        if isinstance(node, dict):
            if "_attributes" in node:
                attrs = node["_attributes"]
                for k, v in attrs.items():
                    node[k] = v
                del node["_attributes"]

            for key, value in list(node.items()):
                if isinstance(value, (dict, list)):
                    self._flatten_attributes(value)
        elif isinstance(node, list):
            for item in node:
                self._flatten_attributes(item)
