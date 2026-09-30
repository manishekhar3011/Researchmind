package com.researchmind.controller;

import com.researchmind.dto.DocumentDtos.DocumentResponse;
import com.researchmind.entity.Document;
import com.researchmind.service.DocumentService;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

@RestController
@RequestMapping("/api/documents")
public class DocumentController {

    private final DocumentService documentService;

    public DocumentController(DocumentService documentService) {
        this.documentService = documentService;
    }

    @PostMapping("/upload")
    public DocumentResponse upload(@AuthenticationPrincipal Long userId, @RequestParam("file") MultipartFile file) {
        Document doc = documentService.upload(userId, file);
        return DocumentResponse.from(doc);
    }

    @GetMapping
    public List<DocumentResponse> list(@AuthenticationPrincipal Long userId) {
        return documentService.listForUser(userId).stream().map(DocumentResponse::from).toList();
    }

    @DeleteMapping("/{id}")
    public void delete(@AuthenticationPrincipal Long userId, @PathVariable Long id) {
        documentService.delete(userId, id);
    }
}
