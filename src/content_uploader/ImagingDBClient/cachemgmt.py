from typing import Tuple, Dict
from tempfile import mkdtemp, mkstemp, NamedTemporaryFile
from pathlib import Path
import errno
import os
import hashlib
import json
from datetime import datetime
import hashlib
from . import encdec


class FilesCacheManager:
    def __init__(self, key:str='', 
                chachePath:str='') -> None:
        self.key = key
        if not chachePath:
            self.cachePath = str(Path.home()) + "/.cache/learndb"
            if self.key:
                self.cachePath += "/secure"
        else:            
            self.cachePath = chachePath
        self.cacheIndex = self._loadCacheIndex()
        if not self.cacheIndex:
            self._initCache()
            self.cacheIndex = self._loadCacheIndex()
        self._cleanupUnindexedFiles()

    def lookup(self, fileURL:str) -> bool:
        result = False
        if "index" in self.cacheIndex:
            if fileURL in self.cacheIndex["index"]:
                result = True
        return result

    def getChecksum(self, fileURL:str) -> bytes:
        checksum = b''
        if self.lookup(fileURL):
            checksum = self.cacheIndex["index"][fileURL]["checksum"]
        return checksum

    def getFileCachingDate(self, fileURL:str) -> datetime:
        fileDate = datetime.fromtimestamp(0)  # start of epoch: oldest file date
        if self.lookup(fileURL):
            fileDate = datetime.fromtimestamp(
                                self.cacheIndex["index"][fileURL]["timestamp"])
        return fileDate

    def getFileType(self, fileURL:str) -> str:
        fileType = ''
        if self.lookup(fileURL):
            fileType = self.cacheIndex["index"][fileURL]["file-type"]
        return fileType

    def getOriginalFilename(self, fileURL:str) -> str:
        originalFilename = ''
        if self.lookup(fileURL):
            originalFilename = self.cacheIndex["index"][fileURL]["original-filename"]
        return originalFilename       

    def getFileContent(self, fileURL:str) -> bytes:
        if not self.lookup(fileURL):
            raise FileNotFoundError(errno.ENOENT, 
                                    os.strerror(errno.ENOENT), 
                                    fileURL)
        return self._loadLocalFile(
                        self.cacheIndex["index"][fileURL]["filename"])

    def cache(self, fileURL: str, content:bytes, 
                fileType:str="application/octet-stream",
                originalFilename='') -> bool:
        checksum = hashlib.md5(content).hexdigest()
        cachingTimestamp = datetime.now().timestamp()
        localFilename = self._storeFileLocally(content)
        if not self.cacheIndex or "index" not in self.cacheIndex:
            self.cacheIndex = self._loadCacheIndex()
            if not self.cacheIndex:
                self._initCache()
                self.cacheIndex = self._loadCacheIndex()
        self.cacheIndex["index"][fileURL] = {
            "filename": localFilename,
            "timestamp": cachingTimestamp,
            "checksum": checksum,
            "file-type": fileType,
            "original-filename": originalFilename
        }
        return self._updateCacheIndex()

    def _storeFileLocally(self, content:bytes, path:str='') -> str:
        if not path:
            tf = NamedTemporaryFile(dir=self.cachePath, delete=False)
        else:
            tf = open(path, 'wb')
        
        if not self.key:
            tf.write(content)
        else:
            encContents = encdec.password_encrypt(content, password=self.key)
            tf.write(encContents)
        
        tf.close()
        return os.path.basename(tf.name if not path else path)

    def _loadLocalFile(self, filename:str) -> bytes:
        content = b''
        filePath = self.cachePath + '/' + filename
        with open(filePath, 'rb') as localFile:
            content = localFile.read()
        if self.key:
            # decrypt the file content using self.key
            content = encdec.password_decrypt(content, password=self.key)
        return content
    
    def _getLocalFilePath(self, fileURL:str) -> str:
        ...

    def _loadCacheIndex(self) -> Dict:
        cacheIndex = {}
        if not os.path.isdir(self.cachePath + "/metadata"):
            print("Cannot find the cache metadata. Needs initialisation?")
            return cacheIndex

        if self.key:
            if os.path.exists(self.cachePath + "/metadata/index.bin"):
                cacheIndex = json.loads(self._loadLocalFile("metadata/index.bin"))
        else:
            indexPath = self.cachePath + "/metadata/index.json"
            if os.path.exists(indexPath):
                with open(indexPath, 'r') as cacheindexFile:
                    cacheIndex = json.load(cacheindexFile)
        return cacheIndex

    def _updateCacheIndex(self) -> bool:
        # Currently this method operates assuming cache use in single threaded 
        # mode. If this changes then this method should be made reentrant
        result = False
        if not self.cacheIndex:
            return False
        cacheIndexContent = json.dumps(self.cacheIndex, indent=4)
        if self.key:
            indexPath = self.cachePath + "/metadata/index.bin"
            self._storeFileLocally(cacheIndexContent.encode("utf8"), indexPath)
            if os.path.isfile(indexPath):
                result = True
        else:
            indexPath = self.cachePath + "/metadata/index.json"
            with open(indexPath, 'w') as indexFile:
                if indexFile.write(cacheIndexContent) >= len(cacheIndexContent):
                    result = True
        return result

    def _initCache(self, forceCreate=False):
        initIndex = {
                    "metadata": {
                        "name":"Local Cache Index",
                        "Description":"Keeps track of locally cached files",
                        "version": "0.0.1"
                    },
                    "index": {
                    }
                }
        Path(self.cachePath + "/metadata").mkdir(parents=True, exist_ok=True)
        indexPath = self.cachePath + '/metadata/index' \
                                + ('.bin' if self.key else '.json')
        if not os.path.exists(indexPath) or forceCreate:
            self.cacheIndex = initIndex
            self._updateCacheIndex()

    def _cleanupUnindexedFiles(self):
        if self.cacheIndex \
                and "index" in self.cacheIndex\
                and self.cacheIndex["index"]:

            indexedFiles = [f[1]["filename"] 
                                for f in self.cacheIndex["index"].items()]
            allFiles = [f for f in os.listdir(self.cachePath) 
                        if not os.path.isdir(os.path.join(self.cachePath,f))]

            filesToBeDeleted = list(set(allFiles) - set(indexedFiles))
            for filename in filesToBeDeleted:
                os.remove(os.path.join(self.cachePath, filename))
