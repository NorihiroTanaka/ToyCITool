from urllib.parse import urlparse, urlunparse
import logging

logger = logging.getLogger(__name__)

def inject_auth_token(url: str, access_token: str) -> str:
    """
    Git URLにアクセストークンを埋め込みます。
    
    Args:
        url (str): 元のリポジトリURL
        access_token (str): アクセストークン

    Returns:
        str: トークンが埋め込まれたURL。スキームがhttp/httpsでない場合は元のURLを返します。
    """
    if not access_token:
        return url

    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https'):
        # netlocにはuser:pass@hostが含まれるが、単純に置換する
        # 既存の認証情報がある場合は上書きする
        new_netloc = f"{access_token}@{parsed.hostname}"
        if parsed.port:
            new_netloc += f":{parsed.port}"
        return urlunparse(parsed._replace(netloc=new_netloc))
    else:
        logger.warning("アクセストークンが提供されましたが、URLスキームが http/https ではありません。トークンを無視します。")
        return url

def mask_auth_token(url: str, access_token: str) -> str:
    """
    URLに含まれるアクセストークンをマスクします。
    
    Args:
        url (str): トークンが含まれる可能性のあるURL
        access_token (str): マスク対象のトークン

    Returns:
        str: トークンがマスクされたURL
    """
    if not access_token:
        return url
    return url.replace(access_token, "*****")
