import asyncio
import kopf
import kubernetes_asyncio
import logging
import os

from base64 import b64decode
from copy import deepcopy
from infinite_relative_backoff import InfiniteRelativeBackoff

operator_domain = os.environ.get('OPERATOR_DOMAIN', 'rhpds.redhat.com')
operator_version = os.environ.get('OPERATOR_VERSION', 'v1')

api_client = core_v1_api = custom_objects_api = None

async def create_oauthclient(definition, logger):
    name = definition['metadata']['name']
    ret = await custom_objects_api.create_cluster_custom_object(
        body=definition,
        group='oauth.openshift.io',
        plural='oauthclients',
        version='v1',
    )
    logger.info(f"Created OAuthClient {name}")
    return ret

async def delete_oauthclient(name, logger):
    try:
        return await custom_objects_api.delete_cluster_custom_object(
            group='oauth.openshift.io',
            name=name,
            plural='oauthclients',
            version='v1',
        )
        logger.info(f"Deleted OAuthClient {name}")
    except kubernetes_asyncio.client.rest.ApiException as exception:
        if exception.status != 404:
            raise

async def get_oauthclient(name):
    try:
        return await custom_objects_api.get_cluster_custom_object(
            group='oauth.openshift.io',
            name=name,
            plural='oauthclients',
            version='v1',
        )
    except kubernetes_asyncio.client.rest.ApiException as exception:
        if exception.status != 404:
            raise

async def get_secret_value(name, namespace):
    try:
        secret = await core_v1_api.read_namespaced_secret(
            name=name,
            namespace=namespace,
        )
    except kubernetes_asyncio.client.rest.ApiException as exception:
        if exception.status == 404:
            raise kopf.TemporaryError(f"Secret {name} not found in {namespace}")
        else:
            raise

    for key in ('clientSecret', 'key', 'secret', 'token'):
        if key in secret.data:
            return b64decode(secret.data[key]).decode('utf-8')

    raise kopf.TemporaryError(f"Secret {name} in {namespace} missing data.secret")

async def manage_oauthclient(name, spec, logger):
    definition = await oauthclient_definition(name, spec)
    current = await get_oauthclient(name)
    if current:
        await update_oauthclient(current, definition, logger)
    else:
        await create_oauthclient(definition, logger)

async def oauthclient_definition(name, spec):
    ret = dict(
        apiVersion="oauth.openshift.io/v1",
        kind="OAuthClient",
        metadata=dict(
            name=name,
        ),
    )
    for field in (
        'accessTokenInactivityTimeoutSeconds', 
        'accessTokenMaxAgeSeconds',
        'grantMethod',
        'redirectURIs',
        'respondWithChallenges',
        'scopeRestrictions',
    ):
        if field in spec:
            ret[field] = spec[field]

    ret['secret'] = await get_secret_value(
        name=spec['secret']['name'],
        namespace=spec['secret'].get('namespace', 'openshift-config'),
    )

    if 'additionalSecrets' in spec:
        ret['additionalSecrets'] = []
        for secret in spec['additionalSecrets']:
            ret['additionalSecrets'].append(
                await get_secret_value(
                    name=secret['name'],
                    namespace=secret.get('namespace', 'openshift-config'),
                )
            )

    return ret

async def update_oauthclient(current, definition, logger):
    name = definition['metadata']['name']

    updated_definition = deepcopy(current)
    for field in (
        'accessTokenInactivityTimeoutSeconds', 
        'accessTokenMaxAgeSeconds',
        'additionalSecrets',
        'grantMethod',
        'redirectURIs',
        'respondWithChallenges',
        'scopeRestrictions',
        'secret',
    ):
        if field in definition:
            updated_definition[field] = definition[field]
        else:
            updated_definition.pop(field, None)

    if current == updated_definition:
        return current

    ret = await custom_objects_api.replace_cluster_custom_object(
        body=updated_definition,
        group='oauth.openshift.io',
        name=name,
        plural='oauthclients',
        version='v1',
    )
    logger.info(f"Updated OAuthClient {name}")
    return ret

@kopf.on.startup()
async def on_startup(settings: kopf.OperatorSettings, **_):
    global api_client, core_v1_api, custom_objects_api

    # Store last handled configuration in status
    settings.persistence.diffbase_storage = kopf.StatusDiffBaseStorage(field='status.diffBase')

    # Never give up from network errors
    settings.networking.error_backoffs = InfiniteRelativeBackoff()

    # Use operator domain as finalizer
    settings.persistence.finalizer = f"{operator_domain}/openshift-oauthclient-manager"

    # Store progress in status.
    settings.persistence.progress_storage = kopf.StatusProgressStorage(field='status.kopf')

    # Only create events for warnings and errors
    settings.posting.level = logging.WARNING

    # Disable scanning for CustomResourceDefinitions updates
    settings.scanning.disabled = True

    if os.path.exists('/run/secrets/kubernetes.io/serviceaccount/token'):
        kubernetes_asyncio.config.load_incluster_config()
    else:
        await kubernetes_asyncio.config.load_kube_config()

    api_client = kubernetes_asyncio.client.ApiClient()
    core_v1_api = kubernetes_asyncio.client.CoreV1Api(api_client)
    custom_objects_api = kubernetes_asyncio.client.CustomObjectsApi(api_client)

@kopf.on.cleanup()
async def on_cleanup(**_):
    await api_client.close()

@kopf.on.create(operator_domain, operator_version, 'oauthclientconfigs')
async def oauthclientconfig_create(logger, name, spec, **_):
    await manage_oauthclient(name, spec, logger)

@kopf.on.delete(operator_domain, operator_version, 'oauthclientconfigs')
async def oauthclientconfig_delete(logger, name, spec, **_):
    await delete_oauthclient(name, logger)

@kopf.on.resume(operator_domain, operator_version, 'oauthclientconfigs')
async def oauthclientconfig_resume(logger, name, spec, **_):
    await manage_oauthclient(name, spec, logger)

@kopf.on.update(operator_domain, operator_version, 'oauthclientconfigs')
async def oauthclientconfig_update(logger, name, spec, **_):
    await manage_oauthclient(name, spec, logger)

@kopf.daemon(operator_domain, operator_version, 'oauthclientconfigs', cancellation_timeout=1, initial_delay=30)
async def oauthclientconfig_daemon(logger, name, spec, stopped, **_):
    try:
        while not stopped:
            await manage_oauthclient(name, spec, logger)
            await asyncio.sleep(30)
    except asyncio.CancelledError:
        pass
