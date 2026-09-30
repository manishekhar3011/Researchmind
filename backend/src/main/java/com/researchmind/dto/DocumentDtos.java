package com.researchmind.dto;

import com.researchmind.entity.Document;
import java.time.Instant;

public class DocumentDtos {

    public static class DocumentResponse {
        public Long id;
        public String fileName;
        public String fileType;
        public String status;
        public Integer chunkCount;
        public Instant uploadedAt;

        public static DocumentResponse from(Document d) {
            DocumentResponse r = new DocumentResponse();
            r.id = d.getId();
            r.fileName = d.getFileName();
            r.fileType = d.getFileType();
            r.status = d.getStatus().name();
            r.chunkCount = d.getChunkCount();
            r.uploadedAt = d.getUploadedAt();
            return r;
        }
    }
}
