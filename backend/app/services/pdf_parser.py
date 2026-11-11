import csv
import re
from pathlib import Path


PDF_COLUMNS = {
    "invoices": [
        "invoice_id",
        "customer_id",
        "invoice_amount",
        "invoice_date",
        "due_date",
    ],
    "payments": [
        "payment_id",
        "invoice_id",
        "payment_amount",
        "payment_date",
        "payment_status",
    ],
    "bank_transactions": [
        "bank_txn_id",
        "reference_id",
        "bank_amount",
        "transaction_date",
        "transaction_type",
        "duplicate_of",
    ],
}

REQUIRED_PDF_FIELDS = {
    "invoices": {"invoice_id", "invoice_amount"},
    "payments": {"payment_id", "invoice_id", "payment_amount"},
    "bank_transactions": {"reference_id", "bank_amount"},
}

FIELD_ALIASES = {
    "invoice_id": (
        "invoice_id",
        "invoice id",
        "invoice number",
        "invoice no",
        "invoice #",
        "inv no",
        "inv #",
        "bill number",
        "bill no",
    ),
    "customer_id": (
        "customer_id",
        "customer id",
        "customer number",
        "client id",
        "account id",
    ),
    "invoice_amount": (
        "invoice_amount",
        "invoice amount",
        "invoice total",
        "total amount",
        "grand total",
        "amount due",
        "total due",
        "amount",
    ),
    "invoice_date": ("invoice_date", "invoice date", "bill date"),
    "due_date": ("due_date", "due date", "payment due date"),
    "payment_id": (
        "payment_id",
        "payment id",
        "payment reference",
        "payment ref",
        "payment number",
        "payment #",
    ),
    "payment_amount": (
        "payment_amount",
        "payment amount",
        "paid amount",
        "amount paid",
        "amount",
    ),
    "payment_date": ("payment_date", "payment date", "paid date"),
    "payment_status": ("payment_status", "payment status", "payment state"),
    "bank_txn_id": (
        "bank_txn_id",
        "bank transaction id",
        "bank txn id",
        "transaction id",
        "txn id",
    ),
    "reference_id": (
        "reference_id",
        "reference id",
        "payment reference",
        "payment id",
        "transaction reference",
        "reference",
        "reference no",
        "ref no",
    ),
    "bank_amount": (
        "bank_amount",
        "bank amount",
        "transaction amount",
        "credit amount",
        "debit amount",
        "credit",
        "debit",
        "amount",
    ),
    "transaction_date": (
        "transaction_date",
        "transaction date",
        "value date",
        "posting date",
        "date",
    ),
    "transaction_type": (
        "transaction_type",
        "transaction type",
        "transaction details",
        "description",
        "narration",
        "type",
    ),
    "duplicate_of": ("duplicate_of", "duplicate of"),
}


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _field_for_header(value: str, dataset_type: str) -> str | None:
    normalized = _normalize_header(value)
    for field in PDF_COLUMNS[dataset_type]:
        if normalized in {
            _normalize_header(alias)
            for alias in FIELD_ALIASES[field]
        }:
            return field
    return None


def _clean_cell(value: object, field: str) -> str:
    text = " ".join(str(value or "").split())
    if field in {"invoice_amount", "payment_amount", "bank_amount"}:
        text = re.sub(r"\b(?:INR|USD|EUR|GBP)\b", "", text, flags=re.I)
        text = re.sub(r"[\s,$€£₹]", "", text)
    return text


def _make_record(
    values: dict[str, str],
    dataset_type: str,
    page_number: int,
    record_number: int | str = 1,
) -> dict[str, str] | None:
    if not any(value for value in values.values()):
        return None

    if (
        dataset_type == "bank_transactions"
        and not values.get("bank_txn_id")
        and values.get("reference_id")
    ):
        values["bank_txn_id"] = f"PDF-BANK-{page_number}-{record_number}"

    missing = [
        field
        for field in REQUIRED_PDF_FIELDS[dataset_type]
        if not values.get(field)
    ]
    if missing:
        raise ValueError(
            f"PDF page {page_number} has an incomplete data row; "
            "could not extract: " + ", ".join(sorted(missing)) + "."
        )

    return {
        column: values.get(column, "")
        for column in PDF_COLUMNS[dataset_type]
    }


def _table_records(
    table: list[list[object]],
    dataset_type: str,
    page_number: int,
    table_number: int = 1,
) -> list[dict[str, str]]:
    for header_index, header in enumerate(table[:5]):
        if not header:
            continue

        mapped_headers = [
            _field_for_header(str(cell or ""), dataset_type)
            for cell in header
        ]
        if not REQUIRED_PDF_FIELDS[dataset_type].issubset(
            {field for field in mapped_headers if field}
        ):
            continue

        records = []
        for row_number, row in enumerate(table[header_index + 1:], start=1):
            values = {column: "" for column in PDF_COLUMNS[dataset_type]}
            for index, cell in enumerate(row):
                if index < len(mapped_headers) and mapped_headers[index]:
                    cell_value = _clean_cell(
                        cell,
                        mapped_headers[index],
                    )
                    if cell_value:
                        values[mapped_headers[index]] = cell_value

            if any(values.values()):
                record = _make_record(
                    values,
                    dataset_type,
                    page_number,
                    f"{table_number}-{row_number}",
                )
                if record:
                    records.append(record)
        return records

    return []


def _key_value_records(
    text: str,
    dataset_type: str,
    page_number: int,
) -> list[dict[str, str]]:
    aliases = sorted(
        (
            (alias, field)
            for field in PDF_COLUMNS[dataset_type]
            for alias in FIELD_ALIASES[field]
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    values = {column: "" for column in PDF_COLUMNS[dataset_type]}

    for line in text.splitlines():
        labeled_parts = re.split(r"[:=#]", line, maxsplit=1)
        if len(labeled_parts) == 2:
            label, value = labeled_parts
            field = _field_for_header(label.strip(), dataset_type)
            if field and value.strip():
                values[field] = _clean_cell(value, field)
                continue

        for alias, field in aliases:
            pattern = (
                r"^\s*" + r"\s+".join(
                    re.escape(part) for part in alias.split()
                )
                + r"\s*(?:[:=#-]\s*|\s{1,})(.*?)\s*$"
            )
            match = re.match(pattern, line, flags=re.I)
            if match and match.group(1).strip():
                values[field] = _clean_cell(match.group(1), field)
                break

    record = _make_record(values, dataset_type, page_number)
    return [record] if record else []


def _ocr_table_records(
    page: object,
    text_page: object,
    dataset_type: str,
    page_number: int,
) -> list[dict[str, str]]:
    words = page.get_text("words", textpage=text_page)
    lines: list[list[tuple]] = []
    for word in sorted(words, key=lambda item: (item[1], item[0])):
        if not lines or abs(word[1] - lines[-1][0][1]) > 3:
            lines.append([word])
        else:
            lines[-1].append(word)

    for header_index, line in enumerate(lines):
        ordered = sorted(line, key=lambda item: item[0])
        header_fields = []
        index = 0
        while index < len(ordered):
            found = None
            for stop in range(min(index + 4, len(ordered)), index, -1):
                phrase = "".join(
                    _normalize_header(str(word[4]))
                    for word in ordered[index:stop]
                )
                field = _field_for_header(phrase, dataset_type)
                if field:
                    found = (stop, field)
                    break
            if found:
                stop, field = found
                header_fields.append((ordered[index][0], field))
                index = stop
            else:
                index += 1

        if not REQUIRED_PDF_FIELDS[dataset_type].issubset(
            {field for _, field in header_fields}
        ):
            continue

        header_fields.sort()
        records = []
        for row_number, data_line in enumerate(
            lines[header_index + 1:],
            start=1,
        ):
            values = {column: "" for column in PDF_COLUMNS[dataset_type]}
            for word in sorted(data_line, key=lambda item: item[0]):
                column_index = max(
                    (
                        position
                        for position, (start_x, _) in enumerate(header_fields)
                        if word[0] >= start_x
                    ),
                    default=-1,
                )
                if column_index >= 0:
                    field = header_fields[column_index][1]
                    values[field] = " ".join(
                        part for part in (values[field], str(word[4])) if part
                    )

            if any(values.values()):
                record = _make_record(
                    values,
                    dataset_type,
                    page_number,
                    row_number,
                )
                if record:
                    records.append(record)
        return records

    return []


def extract_pdf_to_csv(
    pdf_path: Path,
    csv_path: Path,
    dataset_type: str,
) -> dict:
    """Extract tabular or labeled PDF records into the canonical CSV schema."""
    if dataset_type not in PDF_COLUMNS:
        raise ValueError(f"Unsupported PDF dataset type: {dataset_type}.")

    import pdfplumber

    records: list[dict[str, str]] = []
    ocr_used = False

    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            raise ValueError("The PDF contains no pages.")

        for page_number, page in enumerate(pdf.pages, start=1):
            page_records = []
            for table_number, table in enumerate(
                page.extract_tables() or [],
                start=1,
            ):
                page_records.extend(
                    _table_records(
                        table,
                        dataset_type,
                        page_number,
                        table_number,
                    )
                )

            text = page.extract_text() or ""
            if not page_records:
                page_records = _key_value_records(
                    text,
                    dataset_type,
                    page_number,
                )

            if not page_records and not text.strip():
                import pymupdf

                ocr_used = True
                try:
                    with pymupdf.open(pdf_path) as document:
                        ocr_page = document.load_page(page_number - 1)
                        text_page = ocr_page.get_textpage_ocr(
                            language="eng",
                            dpi=300,
                            full=True,
                        )
                        ocr_text = ocr_page.get_text(
                            "text",
                            textpage=text_page,
                        )
                        page_records = _key_value_records(
                            ocr_text,
                            dataset_type,
                            page_number,
                        )
                        if not page_records:
                            page_records = _ocr_table_records(
                                ocr_page,
                                text_page,
                                dataset_type,
                                page_number,
                            )
                except RuntimeError as exc:
                    raise ValueError(
                        "Could not OCR this PDF. Install Tesseract OCR and "
                        "ensure it is available on PATH."
                    ) from exc

            records.extend(page_records)

    if not records:
        raise ValueError(
            "No complete records could be extracted. Use a PDF with "
            "selectable table headers or labeled fields that match this "
            "dataset, or upload a CSV."
        )

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=PDF_COLUMNS[dataset_type])
        writer.writeheader()
        writer.writerows(records)

    return {
        "row_count": len(records),
        "columns": PDF_COLUMNS[dataset_type],
        "ocr_used": ocr_used,
    }
