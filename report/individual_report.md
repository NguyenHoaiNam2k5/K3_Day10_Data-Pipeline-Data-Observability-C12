# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Ngô Hoàng Gia Bảo          |
| MSSV               | 2A202601375                   |
| Khóa/Lớp         | K3                         |
| Tên nhóm         | C12                        |
| Vai trò chính    | Thành viên 5: Integration & Comparison Lead (`phase1.py`, `corruption_flow.py`) |
| Repository         | [K3_Day10_Data-Pipeline-Data-Observability-C12](https://github.com/NguyenHoaiNam2k5/K3_Day10_Data-Pipeline-Data-Observability-C12) |
| Ngày hoàn thành | 2026-08-06                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Baseline Data Pipeline Integration (Phase 1) | [src/pipelines/phase1.py](src/pipelines/phase1.py), [script/run_phase1.py](script/run_phase1.py) | Raw API data / Snapshot, Config settings | Integrated Baseline Pipeline, [data/reports/phase1_report.md](data/reports/phase1_report.md), ChromaDB `papers-baseline` | Hoàn thành |
| Corruption & Repair Flow Integration | [src/pipelines/corruption_flow.py](src/pipelines/corruption_flow.py), [script/run_corruption_flow.py](script/run_corruption_flow.py) | Baseline clean CSV & metrics | End-to-end Corruption -> Evaluate -> Repair -> Compare flow, [data/reports/corruption_report.md](data/reports/corruption_report.md) | Hoàn thành |
| Comparison Report Generation | [src/observability/reporting.py](src/observability/reporting.py) | Metrics (Baseline, Corrupted, Repaired) & Quality reports | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, Markdown reports | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Tích hợp Data Quality Checks vào Pipeline | Thành viên 4 (Observability Lead) | Gọi các hàm `run_data_quality_checks` và `build_freshness_report` tự động trong luồng Phase 1 và Corruption flow. |
| Phối hợp RAG Evaluation Engine | Thành viên 3 (RAG Evaluation Lead) | Đưa bộ benchmark testset vào pipeline đánh giá tự động và xử lý timeout / fallback cho LLM Judge. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ----------------- | ------------- |
| Tích hợp & Chạy thử Baseline Pipeline (Phase 1) | [src/pipelines/phase1.py](src/pipelines/phase1.py) | Pipeline 6 bước hoàn chỉnh, Clean Data (24 rows), Vector store baseline | `python script/run_phase1.py` |
| Xây dựng luồng So sánh Corruption & Repair | [src/pipelines/corruption_flow.py](src/pipelines/corruption_flow.py) | Pipeline 7 bước mô phỏng suy hao dữ liệu, sửa chữa và so sánh | `python script/run_corruption_flow.py` |
| Xuất Báo cáo So sánh tổng hợp | [data/reports/corruption_report.md](data/reports/corruption_report.md) | Báo cáo markdown tổng hợp chỉ số Baseline vs Corrupted vs Repaired | Đọc file [data/reports/corruption_report.md](data/reports/corruption_report.md) |

**Artifact cụ thể do Thành viên 5 tạo ra/kiểm chứng:**
- File báo cáo Phase 1: [data/reports/phase1_report.md](data/reports/phase1_report.md)
- File báo cáo Comparison Report: [data/reports/corruption_report.md](data/reports/corruption_report.md)

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Là Thành viên 5 (Integration & Comparison Lead), nhiệm vụ chính là liên kết toàn bộ các thành phần rời rạc (Ingestion, Data Cleaning, Vector Indexing, Observability Checks, RAG Evaluation Engine) thành các luồng pipeline tự động hóa hoàn chỉnh (`phase1.py` và `corruption_flow.py`), đồng thời thực hiện thực nghiệm so sánh tác động của suy giảm dữ liệu đối với hiệu năng RAG Agent.

### Cách triển khai

1. **Phase 1 Baseline Pipeline Integration (`phase1.py`)**:
   - Bước 1: Gọi Ingestion module nạp dữ liệu thô bài báo từ Crossref.
   - Bước 2: Gọi Cleaning module làm sạch và lưu DataFrame clean sang CSV/JSON.
   - Bước 3: Đưa dữ liệu clean vào ChromaDB vector index (`papers-baseline`).
   - Bước 4: Tạo/Đóng băng bộ benchmark test set (32 câu hỏi).
   - Bước 5: Chạy RAG Evaluation tính `retrieval_hit_rate`, `mean_token_f1`, và `judge_accuracy`.
   - Bước 6: Chạy Data Observability (Quality & Freshness checks) và tự động xuất báo cáo `phase1_report.md`.

2. **Corruption & Repair Flow Integration (`corruption_flow.py`)**:
   - Bước 1: Load dữ liệu baseline clean và metrics baseline.
   - Bước 2: Tiêm lỗi dữ liệu (Data Corruption: xóa tóm tắt, cắt ngắn tiêu đề, sửa ngày xuất bản, tạo trùng ID).
   - Bước 3: Rebuild vector index cho Corrupted dataset (`papers-corrupted`).
   - Bước 4: Đánh giá lại RAG Agent trên bộ test set cũ để ghi nhận suy hao hiệu năng.
   - Bước 5: Sửa dữ liệu (Repair) bằng cách re-ingest và re-clean từ nguồn snapshot thô.
   - Bước 6: Rebuild vector index cho Repaired dataset (`papers-repaired`) và đánh giá lại.
   - Bước 7: Xuất báo cáo so sánh đối chiếu [data/reports/corruption_report.md](data/reports/corruption_report.md).

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Project Settings, Crossref Raw Snapshot, Baseline Clean Data CSV |
| Output                         | ChromaDB Collections, Benchmark Metrics JSONs, Markdown Comparison Reports |
| Module phụ thuộc             | `ingestion.crossref`, `ingestion.cleaning`, `ingestion.corruption`, `retrieval.index`, `evaluation.metrics`, `observability.quality`, `observability.reporting` |
| Module sử dụng output        | Báo cáo nghiệm thu dự án, Dashboard theo dõi pipeline |
| Điều kiện lỗi cần xử lý | Lỗi thiếu baseline metrics khi chạy corruption flow, lỗi timeout LLM Judge |

### Cách xác minh

```bash
.\.venv\Scripts\python script/run_phase1.py
.\.venv\Scripts\python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả 2 pipeline đều hoàn thành mà không có lỗi ngắt đứt, xuất đầy đủ metrics và 2 file báo cáo markdown.
- **Kết quả thực tế:** Pipeline Phase 1 hoàn thành 6/6 bước, Pipeline Corruption Flow hoàn thành 7/7 bước, sinh các báo cáo tại `data/reports/`.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi điều phối luồng đánh giá RAG Evaluation trong `corruption_flow.py`, nếu LLM Judge gặp lỗi kết nối API hoặc hết quota, tiến trình chạy bị treo (hang) làm nghẽn toàn bộ pipeline tích hợp.
- **Các phương án đã cân nhắc:**
  1. Dừng pipeline và báo lỗi ngay khi LLM Judge thất bại.
  2. Bổ sung cấu hình `max_retries=1`, `timeout=10.0s` và cơ chế Fallback Heuristic Judge tự động tính Token F1 nếu LLM timeout.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Đảm bảo nguyên tắc tính sẵn sàng và tính liên tục (Reliability & Robustness) của Data Pipeline tích hợp. Pipeline có thể chạy tự động end-to-end mà không bị ngắt đứt giữa chừng, đồng thời vẫn cung cấp số liệu đánh giá có ý nghĩa.
- **Bằng chứng quyết định phù hợp:** Thời gian thực thi toàn bộ luồng tích hợp `corruption_flow.py` giảm xuống còn 35 giây với kết quả so sánh chính xác 100%.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'datasets'` và tiến trình chạy `run_phase1.py` bị đứng ở bước building ChromaDB index.
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_phase1.py` trực tiếp từ PowerShell hệ thống.
- **Nguyên nhân gốc:** Lệnh `python` trên PowerShell gọi Python môi trường toàn cục (thiếu package `datasets`), đồng thời Python mặc định buffer stdout khiến log tiến trình không hiển thị.
- **Cách xử lý:** 
  1. Chỉ định chính xác đường dẫn Python trong venv dự án: `.\.venv\Scripts\python script/run_phase1.py`.
  2. Thiết lập biến môi trường unbuffered `$env:PYTHONUNBUFFERED="1"` để log hiển thị tức thì.
- **Cách xác minh sau khi sửa:** Pipeline chạy thông suốt từ bước 1 đến bước 6/7 và in log đầy đủ.
- **Điều học được:** Khi tích hợp pipeline nhiều module, việc quản lý môi trường ảo thực thi đồng nhất là điều kiện tiên quyết.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Dữ liệu từ Crossref đến Vector Index:**
   Dữ liệu thô (raw JSON) được lấy từ Crossref REST API qua truy vấn từ khóa và khoảng thời gian xuất bản. Dữ liệu được đưa qua module `ingestion.cleaning` để trích xuất các trường chuẩn (paper_id, title, published date, authors, summary), làm sạch khoảng trắng và tạo text cho embedding. Sau đó, module `retrieval.index` dùng model `sentence-transformers/all-MiniLM-L6-v2` chuyển đổi văn bản thành vector embedding và lưu trữ persistent vào ChromaDB collection `papers-baseline`.

2. **Cách Evaluation set và Ground-truth IDs đo chất lượng:**
   Benchmark test set (`test_set.json`) chứa câu hỏi, ground truth text và danh sách `ground_truth_doc_ids`. Khi RAG Agent nhận câu hỏi, nó tìm kiếm top-K tài liệu liên quan trong ChromaDB. 
   - `retrieval_hit_rate` kiểm tra xem trong danh sách tài liệu truy vấn được (`retrieved_doc_ids`) có chứa ít nhất 1 ID thuộc `ground_truth_doc_ids` hay không.
   - `mean_token_f1` đo độ đè phủ từ vựng giữa câu trả lời sinh ra và ground truth.
   - LLM Judge đánh giá độ chính xác về mặt nội dung ngữ nghĩa.

3. **Khác biệt giữa Quality checks và Freshness monitoring:**
   - **Quality checks** kiểm tra tính toàn vẹn và tính đúng đắn về mặt cấu trúc dữ liệu tại thời điểm ingest (ví dụ: dữ liệu không bị null, ID không trùng lặp, độ dài tóm tắt đạt chuẩn, tổng số dòng >= 5).
   - **Freshness monitoring** kiểm tra thuộc tính thời gian của dữ liệu (xem dữ liệu bài báo có bị cũ/stale hay không bằng cách so sánh ngày xuất bản gần nhất với ngưỡng quy định, ví dụ: 180 ngày).

4. **Tại sao phải dùng cùng test set cho Baseline, Corrupted và Repaired:**
   Việc đóng băng (freeze) và dùng cố định một bộ test set duy nhất đảm bảo tính nhất quán (Controlled Experiment / Reproducibility). Nhờ đó, bất kỳ sự thay đổi nào về chỉ số (`retrieval_hit_rate`, `token_f1`) giữa 3 trạng thái chỉ đến từ sự suy giảm hoặc phục hồi của chất lượng dữ liệu trong Vector Index, chứ không bị nhiễu do thay đổi câu hỏi kiểm thử.

5. **Tiêu chí đánh giá Repair thành công:**
   Repair được xem là thành công khi:
   - Tất cả các kiểm tra Data Quality & Freshness chuyển từ `FAILED`/`STALE` trở lại trạng thái `PASSED`/`FRESH`.
   - Các chỉ số đo lường hiệu năng RAG Agent (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`) sau khi repair khôi phục hoàn toàn trở lại bằng mức của Baseline (Retrieval Hit Rate đạt 100%, Judge Accuracy đạt 28.12%).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   100.00% |    50.00% |  100.00% | Data corruption làm giảm 50% khả năng truy vấn đúng tài liệu của RAG Agent. |
| `mean_token_f1`      |    0.3292 |    0.1331 |   0.3292 | Khớp từ vựng suy giảm mạnh khi dữ liệu bị xóa tóm tắt hoặc méo mó tiêu đề. |
| `judge_accuracy`     |    28.12% |    12.50% |   28.12% | Tỷ lệ trả lời chính xác của agent bị giảm hơn một nửa khi dữ liệu bị lỗi. |
| `mean_judge_score`   |      2.06 |      1.44 |     2.06 | Điểm số chất lượng trung bình (1-5) giảm từ 2.06 xuống 1.44. |
| Quality checks         |    PASSED |    FAILED |   PASSED | Quality check phát hiện chính xác các lỗi null/empty/duplicate được inject. |
| Freshness status       |     FRESH |     STALE |    FRESH | Monitoring cảnh báo chính xác 3 dòng dữ liệu bị sửa ngày xuất bản quá hạn. |

### Kết luận từ số liệu

1. **Data corruption** (xóa tóm tắt, cắt ngắn tiêu đề, tạo trùng ID, chỉnh lùi ngày xuất bản) $\rightarrow$ **Quality checks chuyển sang FAILED** và **Freshness chuyển sang STALE** (phát hiện 3 dòng stale, 3/6 checks pass) $\rightarrow$ **Retrieval Hit Rate của RAG Agent rơi từ 100% xuống 50%**, Judge Accuracy giảm từ 28.12% xuống 12.50%.
2. **Repair action** (re-ingest và re-clean từ nguồn dữ liệu thô chuẩn Crossref) $\rightarrow$ **Quality & Freshness signals phục hồi hoàn toàn** (6/6 checks PASSED, Freshness FRESH) $\rightarrow$ **Agent metrics phục hồi hoàn toàn trở lại bằng mức Baseline** (Retrieval Hit Rate 100%, Mean Token F1 0.3292, Judge Accuracy 28.12%).

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Corruption làm mất tóm tắt bài báo (`summary`) và cắt hỏng tiêu đề (`title`) ảnh hưởng rõ nhất đến RAG Agent. Lý do là vì vector embedding được tính toán dựa trên nội dung tóm tắt; khi tóm tắt bị rỗng hoặc bị ghi đè, khoảng cách cosine trong không gian vector bị lệch hoàn toàn khiến retriever trả về các tài liệu không liên quan, kéo theo Retrieval Hit Rate và Token F1 giảm thảm hại.

**Kết quả nào khác với kỳ vọng ban đầu?**
Kỳ vọng ban đầu là `judge_accuracy` của baseline sẽ đạt trên 80%. Tuy nhiên, kết quả đạt 28.12% (và Mean Judge Score là 2.06/5.0). Nguyên nhân là do trong bài lab baseline, câu trả lời sinh ra chủ yếu trích xuất câu đầu tiên của summary chứ chưa dùng prompt nâng cao của LLM generator, dẫn đến câu trả lời ngắn gọn chưa đủ bao quát toàn bộ ngữ cảnh ground truth dài.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Là người làm Integration, tôi nhận thấy việc xây dựng luồng pipeline tự động có cơ chế kiểm tra lỗi ở từng công đoạn giúp tiết kiệm thời gian phát hiện sự cố dữ liệu.
2. **Về Data Observability:** Các cảnh báo Quality & Freshness đóng vai trò là "chỉ số báo động sớm" để ngừng luồng nạp dữ liệu xấu vào Vector Store trước khi làm hỏng các agent bên dưới.
3. **Về ảnh hưởng của Data đến RAG Agent:** Chất lượng dữ liệu ảnh hưởng trực tiếp đến hiệu năng của RAG. Sửa chữa dữ liệu (Repair) đúng cách sẽ khôi phục 100% khả năng truy vấn của Agent.

### Nếu có thêm thời gian

Nếu có thêm thời gian, tôi sẽ bổ sung cơ chế Airflow/Dagster DAG orchestration để lập lịch tự động chạy pipeline định kỳ, đồng thời kết hợp hệ thống gửi cảnh báo qua Slack/Telegram Webhook khi Data Quality Check bị FAILED.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Ngô Hoàng Gia Bảo  
**Ngày xác nhận:** 2026-08-06  
