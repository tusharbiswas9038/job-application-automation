# processor/deduplicator.py
import logging
import hashlib
from typing import List, Tuple, Set
from rapidfuzz import fuzz
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DuplicateGroup:
    """Group of duplicate jobs"""
    primary_id: str
    duplicate_ids: List[str]
    similarity_score: float


class JobDeduplicator:
    """Deduplicate jobs using hash and fuzzy matching [web:29][web:31][web:33]"""
    
    def __init__(self, fuzzy_threshold: int = 90):
        """
        Args:
            fuzzy_threshold: Similarity threshold (0-100) [web:33]
                            90-95 for tight matching (fewer false positives)
                            80-85 for looser matching
        """
        self.fuzzy_threshold = fuzzy_threshold
    
    def generate_hash(self, company: str, title: str, location: str) -> str:
        """
        Generate deterministic hash for exact deduplication
        
        Args:
            company: Company name
            title: Job title
            location: Location
        
        Returns:
            Hash string
        """
        # Normalize for consistent hashing
        normalized = f"{company.lower().strip()}|{title.lower().strip()}|{location.lower().strip()}"
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def find_duplicates(self, jobs: List) -> List[DuplicateGroup]:
        """
        Find duplicate jobs using hash + fuzzy matching [web:29][web:31]
        
        Args:
            jobs: List of NormalizedJob objects
        
        Returns:
            List of DuplicateGroup objects
        """
        duplicate_groups = []
        seen_hashes: Set[str] = set()
        processed_indices: Set[int] = set()
        
        # First pass: exact hash matching
        hash_groups = {}
        for i, job in enumerate(jobs):
            job_hash = self.generate_hash(job.company, job.title, job.location)
            
            if job_hash in hash_groups:
                hash_groups[job_hash].append(i)
            else:
                hash_groups[job_hash] = [i]
        
        # Record exact duplicates
        for job_hash, indices in hash_groups.items():
            if len(indices) > 1:
                duplicate_groups.append(DuplicateGroup(
                    primary_id=jobs[indices[0]].external_id,
                    duplicate_ids=[jobs[i].external_id for i in indices[1:]],
                    similarity_score=100.0
                ))
                processed_indices.update(indices)
        
        # Second pass: fuzzy matching on non-duplicates [web:29][web:31]
        if self.fuzzy_threshold < 100:
            unprocessed = [i for i in range(len(jobs)) if i not in processed_indices]
            
            for i in range(len(unprocessed)):
                if unprocessed[i] in processed_indices:
                    continue
                
                job1 = jobs[unprocessed[i]]
                similar_jobs = []
                
                for j in range(i + 1, len(unprocessed)):
                    if unprocessed[j] in processed_indices:
                        continue
                    
                    job2 = jobs[unprocessed[j]]
                    
                    # Only compare jobs from same company
                    if job1.company.lower() != job2.company.lower():
                        continue
                    
                    # Calculate fuzzy similarity [web:31]
                    title_similarity = fuzz.ratio(
                        job1.title.lower(),
                        job2.title.lower()
                    )
                    
                    location_similarity = fuzz.ratio(
                        job1.location.lower(),
                        job2.location.lower()
                    )
                    
                    # Combined score (weighted more toward title)
                    combined_score = (title_similarity * 0.7 + location_similarity * 0.3)
                    
                    if combined_score >= self.fuzzy_threshold:
                        similar_jobs.append((unprocessed[j], combined_score))
                        processed_indices.add(unprocessed[j])
                
                if similar_jobs:
                    duplicate_groups.append(DuplicateGroup(
                        primary_id=job1.external_id,
                        duplicate_ids=[jobs[idx].external_id for idx, _ in similar_jobs],
                        similarity_score=sum(score for _, score in similar_jobs) / len(similar_jobs)
                    ))
                    processed_indices.add(unprocessed[i])
        
        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        return duplicate_groups
    
    def mark_duplicates(self, jobs: List, duplicate_groups: List[DuplicateGroup]) -> List:
        """
        Mark jobs as duplicates in place
        
        Args:
            jobs: List of jobs
            duplicate_groups: Groups of duplicates
        
        Returns:
            List of unique jobs
        """
        # Create mapping of duplicate IDs to primary IDs
        duplicate_map = {}
        for group in duplicate_groups:
            for dup_id in group.duplicate_ids:
                duplicate_map[dup_id] = group.primary_id
        
        # Filter out duplicates
        unique_jobs = []
        for job in jobs:
            if job.external_id in duplicate_map:
                logger.debug(f"Marking as duplicate: {job.external_id} -> {duplicate_map[job.external_id]}")
            else:
                unique_jobs.append(job)
        
        logger.info(f"Deduplication: {len(jobs)} -> {len(unique_jobs)} jobs")
        return unique_jobs

