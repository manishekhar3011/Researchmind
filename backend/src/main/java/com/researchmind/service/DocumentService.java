package com.researchmind.service;

import com.researchmind.entity.Document;
import com.researchmind.repository.DocumentRepository;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

import java.io.IOException;
import java.util.List;
import java.util.Map;

@Service
public class DocumentService {

    private final DocumentRepository documentRepository;
    private final RestTemplate restTemplate;

    @Value("${app.ai-service.base-url}")
    private String aiServiceBaseUrl;

    public DocumentService(DocumentRepository documentRepository, RestTemplate restTemplate) {
        this.documentRepository = documentRepository;
        this.restTemplate = restTemplate;
    }

    public Document upload(Long userId, MultipartFile file) {
        String fileName = file.getOriginalFilename() != null ? file.getOriginalFilename() : "unnamed";
        String fileType = fileName.contains(".") ? fileName.substring(fileName.lastIndexOf('.') + 1).toLowerCase() : "";

        if (!List.of("pdf", "docx", "txt").contains(fileType)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Unsupported file type: " + fileType);
        }

        Document doc = new Document();
        doc.setUserId(userId);
        doc.setFileName(fileName);
        doc.setFileType(fileType);
        doc.setStatus(Document.Status.PENDING);
        doc = documentRepository.save(doc);

        try {
            doc.setStatus(Document.Status.PROCESSING);
            documentRepository.save(doc);

            Map<String, Object> ingestResult = callIngest(doc.getId(), file);

            doc.setStatus(Document.Status.READY);
            doc.setChunkCount(((Number) ingestResult.get("chunk_count")).intValue());
            documentRepository.save(doc);
        } catch (Exception e) {
            doc.setStatus(Document.Status.FAILED);
            documentRepository.save(doc);
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "Ingestion failed: " + e.getMessage());
        }

        return doc;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> callIngest(Long documentId, MultipartFile file) throws IOException {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("document_id", documentId);
        body.add("file", new ByteArrayResource(file.getBytes()) {
            @Override
            public String getFilename() {
                return file.getOriginalFilename();
            }
        });

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
        return restTemplate.postForObject(aiServiceBaseUrl + "/internal/ingest", requestEntity, Map.class);
    }

    public List<Document> listForUser(Long userId) {
        return documentRepository.findByUserId(userId);
    }

    public void delete(Long userId, Long documentId) {
        Document doc = documentRepository.findByIdAndUserId(documentId, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Document not found"));

        restTemplate.delete(aiServiceBaseUrl + "/internal/ingest/" + doc.getId());
        documentRepository.delete(doc);
    }
}
