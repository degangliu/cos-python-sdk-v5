# -*- coding=utf-8

import hashlib
import base64
import os
import sys
import xml.dom.minidom
import xml.etree.ElementTree
from urllib import quote
from xml2dict import Xml2Dict
from dicttoxml import dicttoxml
from cos_exception import CosClientError
from cos_exception import CosServiceError

# kwargs中params到http headers的映射
maplist = {
            'ContentLength': 'Content-Length',
            'ContentMD5': 'Content-MD5',
            'ContentType': 'Content-Type',
            'CacheControl': 'Cache-Control',
            'ContentDisposition': 'Content-Disposition',
            'ContentEncoding': 'Content-Encoding',
            'ContentLanguage': 'Content-Language',
            'Expires': 'Expires',
            'ResponseContentType': 'response-content-type',
            'ResponseContentLanguage': 'response-content-language',
            'ResponseExpires': 'response-expires',
            'ResponseCacheControl': 'response-cache-control',
            'ResponseContentDisposition': 'response-content-disposition',
            'ResponseContentEncoding': 'response-content-encoding',
            'Metadata': 'Metadata',
            'ACL': 'x-cos-acl',
            'GrantFullControl': 'x-cos-grant-full-control',
            'GrantWrite': 'x-cos-grant-write',
            'GrantRead': 'x-cos-grant-read',
            'StorageClass': 'x-cos-storage-class',
            'Range': 'Range',
            'IfMatch': 'If-Match',
            'IfNoneMatch': 'If-None-Match',
            'IfModifiedSince': 'If-Modified-Since',
            'IfUnmodifiedSince': 'If-Unmodified-Since',
            'CopySourceIfMatch': 'x-cos-copy-source-If-Match',
            'CopySourceIfNoneMatch': 'x-cos-copy-source-If-None-Match',
            'CopySourceIfModifiedSince': 'x-cos-copy-source-If-Modified-Since',
            'CopySourceIfUnmodifiedSince': 'x-cos-copy-source-If-Unmodified-Since',
            'VersionId': 'x-cos-version-id',
           }


def to_unicode(s):
    if isinstance(s, unicode):
        return s
    else:
        return s.decode('utf-8')


def get_md5(data):
    m2 = hashlib.md5(data)
    MD5 = base64.standard_b64encode(m2.digest())
    return MD5


def dict_to_xml(data):
    """V5使用xml格式，将输入的dict转换为xml"""
    doc = xml.dom.minidom.Document()
    root = doc.createElement('CompleteMultipartUpload')
    doc.appendChild(root)

    if 'Part' not in data.keys():
        raise CosClientError("Invalid Parameter, Part Is Required!")

    for i in data['Part']:
        nodePart = doc.createElement('Part')

        if 'PartNumber' not in i.keys():
            raise CosClientError("Invalid Parameter, PartNumber Is Required!")

        nodeNumber = doc.createElement('PartNumber')
        nodeNumber.appendChild(doc.createTextNode(str(i['PartNumber'])))

        if 'ETag' not in i.keys():
            raise CosClientError("Invalid Parameter, ETag Is Required!")

        nodeETag = doc.createElement('ETag')
        nodeETag.appendChild(doc.createTextNode(str(i['ETag'])))

        nodePart.appendChild(nodeNumber)
        nodePart.appendChild(nodeETag)
        root.appendChild(nodePart)
    return doc.toxml('utf-8')


def xml_to_dict(data, origin_str="", replace_str=""):
    """V5使用xml格式，将response中的xml转换为dict"""
    root = xml.etree.ElementTree.fromstring(data)
    xmldict = Xml2Dict(root)
    xmlstr = str(xmldict)
    xmlstr = xmlstr.replace("{http://www.qcloud.com/document/product/436/7751}", "")
    xmlstr = xmlstr.replace("{http://www.w3.org/2001/XMLSchema-instance}", "")
    if origin_str:
        xmlstr = xmlstr.replace(origin_str, replace_str)
    xmldict = eval(xmlstr)
    return xmldict


def get_id_from_xml(data, name):
    """解析xml中的特定字段"""
    tree = xml.dom.minidom.parseString(data)
    root = tree.documentElement
    result = root.getElementsByTagName(name)
    # use childNodes to get a list, if has no child get itself
    return result[0].childNodes[0].nodeValue


def mapped(headers):
    """S3到COS参数的一个映射"""
    _headers = dict()
    for i in headers.keys():
        if i in maplist:
            _headers[maplist[i]] = headers[i]
        else:
            raise CosClientError('No Parameter Named '+i+' Please Check It')
    return _headers


def format_xml(data, root, lst=list()):
    """将dict转换为xml"""
    xml_config = dicttoxml(data, item_func=lambda x: x, custom_root=root, attr_type=False)
    for i in lst:
        xml_config = xml_config.replace(i+i, i)
    return xml_config


def format_region(region):
    """格式化地域"""
    if region.find('cos.') != -1:
        return region  # 传入cos.ap-beijing-1这样显示加上cos.的region
    if region == 'cn-north' or region == 'cn-south' or region == 'cn-east' or region == 'cn-south-2' or region == 'cn-southwest' or region == 'sg':
        return region  # 老域名不能加cos.
    #  支持v4域名映射到v5
    if region == 'cossh':
        return 'cos.ap-shanghai'
    if region == 'cosgz':
        return 'cos.ap-guangzhou'
    if region == 'cosbj':
        return 'cos.ap-beijing'
    if region == 'costj':
        return 'cos.ap-beijing-1'
    if region == 'coscd':
        return 'cos.ap-chengdu'
    if region == 'cossgp':
        return 'cos.ap-singapore'
    if region == 'coshk':
        return 'cos.ap-hongkong'
    if region == 'cosca':
        return 'cos.na-toronto'
    if region == 'cosger':
        return 'cos.eu-frankfurt'

    return 'cos.' + region  # 新域名加上cos.


def format_bucket(bucket, appid):
    """兼容新老bucket长短命名,appid为空默认为长命名,appid不为空则认为是短命名"""
    if not isinstance(bucket, str):
        raise CosClientError("bucket is not str")
    # appid为空直接返回bucket
    if appid == "":
        return bucket
    # appid不为空,检查是否以-appid结尾
    if bucket.endswith("-"+appid):
        return bucket
    return bucket + "-" + appid


def get_copy_source_info(CopySource):
    """获取拷贝源的所有信息"""
    appid = None
    if 'Appid' in CopySource.keys():
        appid = CopySource['Appid']
    if 'Bucket' in CopySource.keys():
        bucket = CopySource['Bucket']
        bucket = format_bucket(bucket, appid)
    else:
        raise CosClientError('CopySource Need Parameter Bucket')
    if 'Region' in CopySource.keys():
        region = CopySource['Region']
        region = format_region(region)
    else:
        raise CosClientError('CopySource Need Parameter Region')
    if 'Key' in CopySource.keys():
        path = CopySource['Key']
        if path and path[0] == '/':
            path = path[1:]
    else:
        raise CosClientError('CopySource Need Parameter Key')
    return bucket, path, region


def gen_copy_source_url(CopySource):
    """拼接拷贝源url"""
    bucket, path, region = get_copy_source_info(CopySource)
    url = "{bucket}.{region}.myqcloud.com/{path}".format(
            bucket=bucket,
            region=region,
            path=path
            )
    return url
