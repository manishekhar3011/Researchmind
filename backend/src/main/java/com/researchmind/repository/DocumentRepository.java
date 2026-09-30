package com.researchmind.repository;

import com.researchmind.entity.Document;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface DocumentRepository extends JpaRepository<Document, Long> {
    List<Document> findByUserId(Long userId);
    Optional<Document> findByIdAndUserId(Long id, Long userId);
}
