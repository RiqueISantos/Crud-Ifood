import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

geolocator = Nominatim(user_agent="ifood_clone_app")

class EnderecoService:

    @staticmethod
    def consultar_viacep(cep: str) -> dict:
        cep_limpo = "".join(filter(str.isdigit, str(cep)))
        if len(cep_limpo) != 8:
            raise ValueError("CEP deve conter exatamente 8 dígitos numéricos.")

        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                raise RuntimeError("Falha ao comunicar com o serviço de CEP.")
            
            dados = resp.json()
            if dados.get("erro"):
                raise ValueError("CEP não encontrado.")

            logradouro = dados.get("logradouro", "").strip()
            cep_unico = (logradouro == "")

            return {
                "cep": dados.get("cep"),
                "logradouro": logradouro,
                "bairro": dados.get("bairro", "").strip(),
                "cidade": dados.get("localidade"),
                "uf": dados.get("uf"),
                "cep_unico": cep_unico 
            }
        except requests.RequestException:
            raise RuntimeError("Serviço de CEP indisponível no momento.")

    @staticmethod
    def obter_coordenadas(logradouro: str, numero: str, bairro: str, cidade: str, uf: str, cep: str) -> tuple:
        """
        1. Tenta obter coordenadas diretamente pelo CEP via AwesomeAPI (base brasileira precisa).
        2. Se falhar, busca no Nominatim forçando a inclusão do BAIRRO no texto.
        """
        cep_limpo = "".join(filter(str.isdigit, str(cep)))

        try:
            url = f"https://cep.awesomeapi.com.br/json/{cep_limpo}"
            resp = requests.get(url, timeout=4)
            if resp.status_code == 200:
                dados = resp.json()
                lat = dados.get("lat")
                lng = dados.get("lng")
                if lat and lng:
                    return float(lat), float(lng)
        except Exception:
            pass

        queries = [
            f"{logradouro}, {numero} - {bairro}, {cidade} - {uf}, Brasil",
            f"{logradouro} - {bairro}, {cidade} - {uf}, Brasil",
            f"{bairro}, {cidade} - {uf}, Brasil"
        ]

        for q in queries:
            try:
                local = geolocator.geocode(q, timeout=5)
                if local:
                    return local.latitude, local.longitude
            except (GeocoderTimedOut, Exception):
                continue
            
        try:
            local = geolocator.geocode(f"{cidade} - {uf}, Brasil", timeout=5)
            if local:
                return local.latitude, local.longitude
        except Exception:
            pass

        return None, None