"""
nota_fiscal_service.py — Gera PDF de nota fiscal simulada e envia por e-mail.

Fluxo:
  1. gerar_pdf(pedido)         → gera bytes do PDF com os dados do pedido
  2. emitir_e_notificar(pedido) → gera PDF e envia como anexo via SendGrid
"""

import os
import io
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def _chave_simulada(pedido_id: int) -> str:
    """Gera uma chave de acesso simulada de 44 dígitos."""
    base = f"35{datetime.now().strftime('%y%m')}00000000000000006500100000{pedido_id:09d}1"
    return base[:44].ljust(44, "0")


def gerar_pdf(pedido) -> bytes:
    """
    Gera o PDF da nota fiscal simulada com todos os dados do pedido.
    Retorna os bytes do PDF pronto para ser anexado ou salvo.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    vermelho = colors.HexColor("#EA1D2C")
    cinza    = colors.HexColor("#616161")
    cinza_cl = colors.HexColor("#F5F5F5")

    titulo = ParagraphStyle("titulo", fontSize=22, textColor=vermelho,
                             fontName="Helvetica-Bold", alignment=TA_CENTER)
    subtitulo = ParagraphStyle("subtitulo", fontSize=11, textColor=cinza,
                                alignment=TA_CENTER)
    secao = ParagraphStyle("secao", fontSize=9, textColor=cinza,
                            fontName="Helvetica-Bold", spaceAfter=2)
    corpo = ParagraphStyle("corpo", fontSize=9, textColor=colors.black)
    corpo_dir = ParagraphStyle("corpo_dir", fontSize=9, alignment=TA_RIGHT)
    destaque = ParagraphStyle("destaque", fontSize=11, fontName="Helvetica-Bold",
                               textColor=vermelho, alignment=TA_RIGHT)
    rodape = ParagraphStyle("rodape", fontSize=7, textColor=cinza,
                             alignment=TA_CENTER)

    usuario    = pedido.usuario
    restaurante = pedido.restaurante
    endereco   = pedido.endereco
    chave      = _chave_simulada(pedido.id)
    emitido_em = pedido.criado_em.strftime("%d/%m/%Y %H:%M") if pedido.criado_em else datetime.now().strftime("%d/%m/%Y %H:%M")

    elementos = []

    # ── Cabeçalho ──────────────────────────────────────────────────────────
    elementos.append(Paragraph("iFood", titulo))
    elementos.append(Paragraph("NOTA FISCAL DO CONSUMIDOR ELETRÔNICA — NFC-e (SIMULAÇÃO)", subtitulo))
    elementos.append(Spacer(1, 4*mm))
    elementos.append(HRFlowable(width="100%", thickness=1.5, color=vermelho))
    elementos.append(Spacer(1, 4*mm))

    # ── Emitente ────────────────────────────────────────────────────────────
    elementos.append(Paragraph("EMITENTE", secao))
    emitente_data = [
        [Paragraph(f"<b>Restaurante:</b> {restaurante.nome}", corpo),
         Paragraph(f"<b>Pedido Nº:</b> {pedido.id}", corpo_dir)],
        [Paragraph(f"{restaurante.logradouro}, {restaurante.numero} — {restaurante.bairro}", corpo),
         Paragraph(f"<b>Emitido em:</b> {emitido_em}", corpo_dir)],
        [Paragraph(f"{restaurante.cidade} / {restaurante.uf} — CEP {restaurante.cep}", corpo), ""],
    ]
    t = Table(emitente_data, colWidths=["60%", "40%"])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cinza_cl),
        ("BOX",        (0, 0), (-1, -1), 0.5, cinza),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    elementos.append(t)
    elementos.append(Spacer(1, 4*mm))

    # ── Destinatário ────────────────────────────────────────────────────────
    elementos.append(Paragraph("DESTINATÁRIO", secao))
    end_str = ""
    if endereco:
        end_str = f"{endereco.logradouro}, {endereco.numero} — {endereco.bairro}, {endereco.cidade}/{endereco.uf}"
    dest_data = [
        [Paragraph(f"<b>Nome:</b> {usuario.nome if usuario else 'Consumidor'}", corpo),
         Paragraph(f"<b>E-mail:</b> {usuario.email if usuario else '—'}", corpo)],
        [Paragraph(f"<b>Endereço de entrega:</b> {end_str or '—'}", corpo), ""],
    ]
    t2 = Table(dest_data, colWidths=["50%", "50%"])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), cinza_cl),
        ("BOX",        (0, 0), (-1, -1), 0.5, cinza),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("SPAN", (0, 1), (1, 1)),
    ]))
    elementos.append(t2)
    elementos.append(Spacer(1, 4*mm))

    # ── Itens ───────────────────────────────────────────────────────────────
    elementos.append(Paragraph("ITENS DO PEDIDO", secao))
    header = [
        Paragraph("<b>#</b>",          corpo),
        Paragraph("<b>Descrição</b>",  corpo),
        Paragraph("<b>Qtd</b>",        corpo),
        Paragraph("<b>Unit. (R$)</b>", corpo),
        Paragraph("<b>Total (R$)</b>", corpo),
    ]
    linhas = [header]
    for i, item in enumerate(pedido.itens, start=1):
        linhas.append([
            Paragraph(str(i), corpo),
            Paragraph(item.nome_produto, corpo),
            Paragraph(str(item.quantidade), corpo),
            Paragraph(f"{item.preco_unitario:.2f}", corpo),
            Paragraph(f"{item.subtotal_item:.2f}", corpo),
        ])

    t3 = Table(linhas, colWidths=[10*mm, "50%", 15*mm, 25*mm, 25*mm])
    t3.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  vermelho),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, cinza_cl]),
        ("BOX",          (0, 0), (-1, -1), 0.5, cinza),
        ("INNERGRID",    (0, 0), (-1, -1), 0.3, cinza),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("ALIGN",        (2, 0), (-1, -1), "CENTER"),
    ]))
    elementos.append(t3)
    elementos.append(Spacer(1, 4*mm))

    # ── Totais ──────────────────────────────────────────────────────────────
    forma_pgto = pedido.forma_pagamento.value if pedido.forma_pagamento else "—"
    totais = [
        [Paragraph("Subtotal:", corpo),          Paragraph(f"R$ {pedido.subtotal:.2f}", corpo_dir)],
        [Paragraph("Taxa de entrega:", corpo),    Paragraph(f"R$ {pedido.taxa_entrega:.2f}", corpo_dir)],
        [Paragraph("<b>TOTAL:</b>", corpo),       Paragraph(f"<b>R$ {pedido.total:.2f}</b>", destaque)],
        [Paragraph("Forma de pagamento:", corpo), Paragraph(forma_pgto, corpo_dir)],
    ]
    t4 = Table(totais, colWidths=["70%", "30%"])
    t4.setStyle(TableStyle([
        ("LINEABOVE",    (0, 2), (-1, 2), 1, vermelho),
        ("LEFTPADDING",  (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
    ]))
    elementos.append(t4)
    elementos.append(Spacer(1, 6*mm))

    # ── Chave e rodapé ──────────────────────────────────────────────────────
    elementos.append(HRFlowable(width="100%", thickness=0.5, color=cinza))
    elementos.append(Spacer(1, 3*mm))
    elementos.append(Paragraph(f"Chave de acesso (simulação): {chave}", rodape))
    elementos.append(Paragraph(
        "Documento emitido em ambiente de simulação — sem validade fiscal.",
        rodape
    ))

    doc.build(elementos)
    return buffer.getvalue()


def emitir_e_notificar(pedido) -> None:
    """
    Gera o PDF da nota fiscal e envia por e-mail ao usuário via SendGrid.
    Chamado automaticamente pelo simulador quando o status chegar em ENTREGUE.
    """
    usuario = pedido.usuario
    if not usuario or not usuario.email:
        print(f"[NF] Usuário sem e-mail — nota não enviada (pedido {pedido.id})")
        return

    try:
        pdf_bytes = gerar_pdf(pedido)
        print(f"[NF] PDF gerado para pedido {pedido.id} ({len(pdf_bytes)} bytes)")
    except Exception as exc:
        print(f"[NF] Erro ao gerar PDF pedido {pedido.id}: {exc}")
        return

    _enviar_email(
        email=usuario.email,
        nome=usuario.nome,
        pedido=pedido,
        pdf_bytes=pdf_bytes,
    )


def _enviar_email(email: str, nome: str, pedido, pdf_bytes: bytes) -> None:
    """Envia o PDF como anexo via SendGrid."""
    import base64
    sendgrid_key = os.getenv("SENDGRID_API_KEY", "")
    from_email   = os.getenv("SENDGRID_FROM_EMAIL", "")

    html = f"""
    <div style="font-family:Inter,sans-serif;max-width:520px;margin:auto;padding:32px;
                background:#fff;border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,.08)">
      <div style="text-align:center;margin-bottom:20px">
        <span style="font-size:28px;font-weight:800;color:#EA1D2C">iFood</span>
      </div>
      <h2 style="color:#212121;font-size:18px;margin-bottom:8px">Pedido entregue! 🎉</h2>
      <p style="color:#616161">
        Olá, <strong>{nome}</strong>! Seu pedido <strong>#{pedido.id}</strong>
        de <strong>{pedido.restaurante.nome}</strong> foi entregue com sucesso.
      </p>
      <p style="color:#616161">
        A nota fiscal simulada está em anexo neste e-mail (arquivo PDF).
      </p>
      <div style="background:#f5f5f5;border-radius:8px;padding:16px;margin:20px 0;font-size:14px">
        <strong>Resumo do pedido:</strong><br/>
        {"<br/>".join(f"• {i.quantidade}x {i.nome_produto} — R$ {i.subtotal_item:.2f}" for i in pedido.itens)}
        <hr style="border:none;border-top:1px solid #ddd;margin:10px 0"/>
        <strong>Total: R$ {pedido.total:.2f}</strong>
      </div>
      <p style="color:#9e9e9e;font-size:12px;text-align:center;margin-top:24px">
        iFood Clone — obrigado pela preferência!
      </p>
    </div>
    """

    if not sendgrid_key or not from_email:
        print(f"[NF] [DEV] SendGrid não configurado — e-mail não enviado para {email}")
        print(f"[NF] [DEV] PDF gerado com {len(pdf_bytes)} bytes (pedido {pedido.id})")
        return

    try:
        import sendgrid as sg_lib
        from sendgrid.helpers.mail import (
            Mail, Attachment, FileContent, FileName,
            FileType, Disposition
        )

        sg = sg_lib.SendGridAPIClient(api_key=sendgrid_key)

        message = Mail(
            from_email=from_email,
            to_emails=email,
            subject=f"Pedido #{pedido.id} entregue — sua nota fiscal",
            html_content=html,
        )

        anexo = Attachment(
            FileContent(base64.b64encode(pdf_bytes).decode()),
            FileName(f"nota_fiscal_pedido_{pedido.id}.pdf"),
            FileType("application/pdf"),
            Disposition("attachment"),
        )
        message.attachment = anexo

        sg.send(message)
        print(f"[NF] E-mail com PDF enviado para {email} (pedido {pedido.id})")

    except Exception as exc:
        print(f"[NF] Erro ao enviar e-mail: {exc}")
