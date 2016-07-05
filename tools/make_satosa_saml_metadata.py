#!/usr/bin/env python
import argparse
import copy
import logging

from saml2 import md
from saml2 import saml
from saml2 import xmldsig
from saml2 import xmlenc
from saml2.config import Config
from saml2.extension import dri
from saml2.extension import idpdisc
from saml2.extension import mdattr
from saml2.extension import mdrpi
from saml2.extension import mdui
from saml2.extension import shibmd
from saml2.extension import ui
from saml2.metadata import (entity_descriptor, entities_descriptor, sign_entity_descriptor,
                            metadata_tostring_fix)
from saml2.sigver import security_context
from saml2.validate import valid_instance

from satosa.backends.saml2 import SAMLBackend
from satosa.frontends.saml2 import SAMLFrontend
from satosa.frontends.saml2 import SAMLMirrorFrontend
from satosa.plugin_loader import (load_frontends, load_backends)
from satosa.satosa_config import SATOSAConfig

logger = logging.getLogger("")
handler = logging.StreamHandler()
logFormatter = logging.Formatter("[%(name)-12.12s] [%(levelname)-5.5s]  %(message)s")
handler.setFormatter(logFormatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

NSPAIR = {"xs": "http://www.w3.org/2001/XMLSchema"}

ONTS = {
    saml.NAMESPACE: saml,
    mdui.NAMESPACE: mdui,
    mdattr.NAMESPACE: mdattr,
    mdrpi.NAMESPACE: mdrpi,
    dri.NAMESPACE: dri,
    ui.NAMESPACE: ui,
    idpdisc.NAMESPACE: idpdisc,
    md.NAMESPACE: md,
    xmldsig.NAMESPACE: xmldsig,
    xmlenc.NAMESPACE: xmlenc,
    shibmd.NAMESPACE: shibmd
}


def create_config_file(frontend, metadata_desc, backend_name):
    """
    Returns a copy of the frontend_config updated with the given metadata_desc

    :type frontend_config: dict[str, Any]
    :type frontend_endpoints: dict[str, dict[str, str]]
    :type url_base: str
    :type metadata_desc: satosa.metadata_creation.description.MetadataDescription
    :type backend_name: str
    :rtype: dict[str, Any]

    :param frontend_config: Frontend idp config
    :param frontend_endpoints: Frontend endpoints
    :param url_base: proxy base url
    :param metadata_desc: one metadata description of a backend
    :param backend_name: backend name
    :return: An updated frontend idp config
    """
    cnf = copy.deepcopy(frontend.config["idp_config"])
    metadata_desc = metadata_desc.to_dict()
    proxy_id = cnf["entityid"]
    entity_id = metadata_desc["entityid"]

    cnf = _join_dict(cnf, metadata_desc)

    # TODO Only supports the SAMLMirrorFrontend
    cnf = frontend._load_endpoints_to_config(backend_name, entity_id, config=cnf)
    cnf["entityid"] = "{}/{}".format(proxy_id, entity_id)
    return cnf


def _join_dict(dict_a, dict_b):
    """
    Joins two dicts
    :type dict_a: dict[Any, Any]
    :type dict_b: dict[Any, Any]
    :param dict_a: base dict
    :param dict_b: overriding dict
    :return: A joined dict
    """
    for key, value in dict_b.items():
        if key not in dict_a:
            dict_a[key] = value
        elif not isinstance(value, dict):
            dict_a[key] = value
        else:
            dict_a[key] = _join_dict(dict_a[key], dict_b[key])
    return dict_a


def _make_metadata(config_dict, option):
    """
    Creates metadata from the given idp config

    :type config_dict: dict[str, Any]
    :type option: MetadataOption
    :rtype: str

    :param config_dict: config
    :param option: metadata creation settings
    :return: A xml string
    """
    eds = []
    cnf = Config()
    cnf.load(copy.deepcopy(config_dict), metadata_construction=True)

    if option.valid:
        cnf.valid_for = option.valid
    eds.append(entity_descriptor(cnf))

    conf = Config()
    conf.key_file = option.keyfile
    conf.cert_file = option.cert
    conf.debug = 1
    conf.xmlsec_binary = option.xmlsec
    secc = security_context(conf)

    if option.id:
        desc, xmldoc = entities_descriptor(eds, option.valid, option.name, option.id,
                                           option.sign, secc)
        valid_instance(desc)
        print(desc.to_string(NSPAIR))
    else:
        for eid in eds:
            if option.sign:
                assert conf.key_file
                assert conf.cert_file
                eid, xmldoc = sign_entity_descriptor(eid, option.id, secc)
            else:
                xmldoc = None

            valid_instance(eid)
            xmldoc = metadata_tostring_fix(eid, NSPAIR, xmldoc).decode()
            return xmldoc


def make_satosa_metadata(option):
    """
    Creates metadata files from a VOPaaS proxy config
    :type option: MetadataOption
    :param option: The creation settings
    """
    conf_mod = SATOSAConfig(option.config_file)

    frontend_modules = load_frontends(conf_mod, None, conf_mod.INTERNAL_ATTRIBUTES).values()
    backend_modules = load_backends(conf_mod, None, conf_mod.INTERNAL_ATTRIBUTES).values()

    frontend_names = [p.name for p in frontend_modules]
    backend_names = [p.name for p in backend_modules]
    logger.info("Loaded frontend plugins: {}".format(frontend_names))
    logger.info("Loaded backend plugins: {}".format(backend_names))

    backend_metadata = {}
    if option.generate_backend:
        for plugin_module in backend_modules:
            if isinstance(plugin_module, SAMLBackend):
                logger.info("Generating saml backend '%s' metadata..." % plugin_module.name)
                backend_metadata[plugin_module.name] = _make_metadata(plugin_module.config["config"], option)

    frontend_metadata = {}
    if option.generate_frontend:
        for frontend in frontend_modules:
            if isinstance(frontend, SAMLMirrorFrontend):
                frontend_metadata[frontend.name] = []
                for plugin_module in backend_modules:
                    provider = plugin_module.name
                    logger.info(
                        "Creating metadata for frontend '{}' and backend '{}'".format(frontend.name,
                                                                                      provider))

                    meta_desc = backend_modules[provider].get_metadata_desc()
                    for desc in meta_desc:
                        xml = _make_metadata(
                            create_config_file(desc, provider),
                            option
                        )
                        frontend_metadata[frontend.name].append(
                            {"xml": xml, "plugin_name": frontend.name, "entity_id": desc.entity_id}
                        )
            elif isinstance(frontend, SAMLFrontend):
                frontend.register_endpoints(backend_names)
                xml = _make_metadata(frontend.idp_config, option)
                frontend_metadata[frontend.name] = [{"xml": xml, "plugin_name": frontend.name}]

    if option.generate_backend:
        for backend, data in backend_metadata.items():
            path = "%s/%s_backend_metadata.xml" % (option.output, backend)
            logger.info("Writing backend '%s' metadata to '%s'" % (backend, path))
            file = open(path, "w")
            file.write(data)
            file.close()

    if option.generate_frontend:
        for frontend in frontend_metadata:
            for meta in frontend_metadata[frontend]:
                if "entity_id" in meta:
                    path = "{}/{}_{}.xml".format(option.output, meta["plugin_name"],
                                                 meta["entity_id"])
                else:
                    path = "{}/{}.xml".format(option.output, meta["plugin_name"])
                logger.info("Writing metadata '{}".format(path))
                out_file = open(path, 'w')
                out_file.write(meta["xml"])
                out_file.close()

                # combined_metadata = create_combined_metadata(metadata[frontend])
                # if option.output:
                #     out_file = open(option.output, 'w')
                #     out_file.write(combined_metadata)
                #     out_file.close()
                # else:
                #     print(combined_metadata)


class MetadataOption(object):
    """
    Class that holds teh settings for the metadata creation
    """

    def __init__(self, config_file, valid=None, cert=None, id=None, keyfile=None, name="",
                 sign=None, xmlsec=None,
                 generate_frontend=True, generate_backend=True, output=None):
        """
        :type config_file: str
        :type valid: str
        :type cert: str
        :type id: str
        :type keyfile: str
        :type name: str
        :type sign: bool
        :type xmlsec: str
        :type output: str
        :type generate_backend: bool
        :type generate_frontend: bool

        :param config_file: Path to VOPaaS proxy config file
        :param valid: How long, in days, the metadata is valid from the time of creation
        :param cert: Path to cert file
        :param id: The ID of the entities descriptor
        :param keyfile: A file with a key to sign the metadata with
        :param name: entities name
        :param sign: sign the metadata
        :param xmlsec: xmlsec binaries to be used for the signing
        :param generate_backend: Generate backend
        :param generate_frontend: Generate frontend
        :param output: Where to write metadata files
        """
        self.config_file = config_file
        self.valid = int(valid) * 24 if valid else 0
        self.cert = cert
        self.id = id
        self.keyfile = keyfile
        self.name = name
        self.sign = sign
        self.xmlsec = xmlsec
        self.generate_frontend = generate_frontend
        self.generate_backend = generate_backend
        self.output = output

    def __str__(self):
        return str(self.__dict__)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', dest='valid',
                        help="How long, in days, the metadata is valid from the time of creation")
    parser.add_argument('-c', dest='cert', help='certificate')
    parser.add_argument('-i', dest='id',
                        help="The ID of the entities descriptor")
    parser.add_argument('-k', dest='keyfile',
                        help="A file with a key to sign the metadata with")
    parser.add_argument('-n', dest='name', default="")
    parser.add_argument('-s', dest='sign', action='store_true',
                        help="sign the metadata")
    parser.add_argument('-x', dest='xmlsec',
                        help="xmlsec binaries to be used for the signing")
    parser.add_argument('-f', dest="frontend", help='generate frontend metadata',
                        action="store_true")
    parser.add_argument('-b', dest="backend", help='generate backend metadata', action="store_true")
    parser.add_argument('-o', dest='output', default=".", help="Where to write metadata files")
    parser.add_argument(dest="config")
    args = parser.parse_args()

    generate_frontend = args.frontend
    generate_backend = args.backend

    # If no generate frontend/backend option, generate both
    if not (args.frontend or args.backend):
        generate_frontend = True
        generate_backend = True

    logger.info("Generating: frontends: %s, backends: %s" % (generate_frontend, generate_backend))

    logger.info("Generating metadata for proxy config: '{}'".format(args.config))
    option = MetadataOption(args.config, args.valid, args.cert, args.id, args.keyfile, args.name,
                            args.sign, args.xmlsec,
                            generate_frontend, generate_backend, args.output)
    logger.info("Settings: {}".format(option))
    make_satosa_metadata(option)
