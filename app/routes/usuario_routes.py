import traceback
from flask import Blueprint, request, jsonify
from app.database import SessionLocal
from app.controllers.usuario_controller import UsuarioController
from app.views.usuario_view import UsuarioView
from auth_service import OtpService
from auth import token_obrigatorio
from auth import criar_token_jwt
from twilio.base.exceptions import TwilioRestException

usuario_bp = Blueprint("usuario", __name__)

servico_otp = OtpService()


@usuario_bp.route("/sms/enviar", methods=["POST"])
def enviar_sms_numero():
    dados    = request.get_json() or {}
    telefone = dados.get("telefone", "").strip()

    if not telefone:
        return jsonify({"erro": "Telefone é obrigatório."}), 400

    db = SessionLocal()
    try:
        controller = UsuarioController(db, sms_service=servico_otp)
        controller.enviar_codigo(destino=telefone, canal="sms", tipo_fluxo="cadastro")
        return jsonify({"mensagem": "Código enviado pelo WhatsApp/SMS."}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except TwilioRestException:
        return jsonify({"erro": "Não foi possível enviar o código. Verifique o número."}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/sms/verificar", methods=["POST"])
def verificar_sms_numero():
    dados    = request.get_json() or {}
    telefone = dados.get("telefone", "").strip()
    codigo   = dados.get("codigo",   "").strip()

    if not telefone or not codigo:
        return jsonify({"erro": "Telefone e código são obrigatórios."}), 400

    db = SessionLocal()
    try:
        controller = UsuarioController(db, sms_service=servico_otp)
        controller.verificar_codigo(destino=telefone, codigo=codigo, canal="sms")
        return jsonify({"mensagem": "Celular verificado com sucesso."}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/email/enviar", methods=["POST"])
def enviar_email_verificacao():
    dados = request.get_json() or {}
    email = dados.get("email", "").strip()

    if not email:
        return jsonify({"erro": "E-mail é obrigatório."}), 400

    db = SessionLocal()
    try:
        controller = UsuarioController(db, email_service=servico_otp)
        controller.enviar_codigo(destino=email, canal="email", tipo_fluxo="cadastro")
        return jsonify({"mensagem": "Código de verificação enviado para o e-mail."}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/email/verificar", methods=["POST"])
def verificar_email():
    dados  = request.get_json() or {}
    email  = dados.get("email",  "").strip()
    codigo = dados.get("codigo", "").strip()

    if not email or not codigo:
        return jsonify({"erro": "E-mail e código são obrigatórios."}), 400

    db = SessionLocal()
    try:
        controller = UsuarioController(db, email_service=servico_otp)
        controller.verificar_codigo(destino=email, codigo=codigo, canal="email")
        return jsonify({"mensagem": "E-mail verificado com sucesso."}), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/", methods=["POST"])
def criar_usuario():
    dados = request.get_json() or {}
    db    = SessionLocal()
    try:
        controller = UsuarioController(
            db,
            sms_service=servico_otp,
            email_service=servico_otp,
        )
        usuario = controller.criar_usuario(dados)
        return UsuarioView.resposta_unico(usuario, 201)
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/", methods=["GET"])
def listar_usuarios():
    db = SessionLocal()
    try:
        controller = UsuarioController(db)
        usuarios   = controller.listar()
        return UsuarioView.resposta_lista(usuarios, 200)
    finally:
        db.close()


@usuario_bp.route("/<int:id>", methods=["GET"])
@token_obrigatorio
def buscar_usuario(usuario_id, id):
    db = SessionLocal()
    try:
        controller = UsuarioController(db)
        usuario    = controller.buscar(id)
        return UsuarioView.resposta_unico(usuario, 200)
    except ValueError as e:
        return UsuarioView.resposta_mensagem({"erro": str(e)}, 404)
    finally:
        db.close()


@usuario_bp.route("/<int:id>", methods=["PUT"])
@token_obrigatorio
def atualizar_usuario(usuario_id, id):
    
    if usuario_id != id:
        return jsonify({"erro": "Você não tem permissão para alterar este usuário."}), 403

    dados = request.get_json() or {}
    db    = SessionLocal()
    try:
        controller = UsuarioController(db)
        usuario    = controller.atualizar(id, dados)
        return UsuarioView.resposta_unico(usuario, 200)
    except ValueError as e:
        status = 404 if "não encontrado" in str(e) else 400
        return UsuarioView.resposta_mensagem({"erro": str(e)}, status)
    finally:
        db.close()


@usuario_bp.route("/<int:id>", methods=["DELETE"])
@token_obrigatorio
def deletar_usuario(usuario_id, id): 
    
    if usuario_id != id:
        return jsonify({"erro": "Você não tem permissão para deletar este usuário."}), 403

    db = SessionLocal()
    try:
        controller = UsuarioController(db)
        resultado  = controller.deletar(id)
        return UsuarioView.resposta_mensagem(resultado, 200)
    except ValueError as e:
        return UsuarioView.resposta_mensagem({"erro": str(e)}, 404)
    finally:
        db.close()


@usuario_bp.route("/login/solicitar", methods=["POST"])
def solicitar_codigo_login():
    dados = request.get_json() or {}
    identificador = dados.get("identificador", "").strip() 
    canal = dados.get("canal", "").strip().lower()

    if not identificador:
        return jsonify({"erro": "Identificador (e-mail ou telefone) é obrigatório."}), 400

    if not canal:
        canal = "email" if "@" in identificador else "sms"

    db = SessionLocal()
    try:
        controller = UsuarioController(
            db, 
            sms_service=servico_otp, 
            email_service=servico_otp
        )
        controller.enviar_codigo(destino=identificador, canal=canal, tipo_fluxo="login")
        return jsonify({"mensagem": f"Código de login enviado via {canal.upper()}."}), 200

    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except TwilioRestException:
        return jsonify({"erro": "Falha ao enviar mensagem pela Twilio. Verifique o contato."}), 400
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()


@usuario_bp.route("/login", methods=["POST"])
def login():
    dados = request.get_json() or {}
    identificador = dados.get("identificador", "").strip()
    codigo        = dados.get("codigo", "").strip()
    canal         = dados.get("canal", "").strip().lower()

    if not identificador or not codigo:
        return jsonify({"erro": "Identificador e código são obrigatórios."}), 400

    if not canal:
        canal = "email" if "@" in identificador else "sms"

    db = SessionLocal()
    try:
        controller = UsuarioController(
            db, 
            sms_service=servico_otp, 
            email_service=servico_otp
        )

        usuario = controller.autenticar_login(identificador=identificador, codigo=codigo, canal=canal)
        
        token = criar_token_jwt(usuario.id)

        return jsonify({
            "mensagem": "Login realizado com sucesso!",
            "access_token": token,
            "token_type": "Bearer",
            "usuario": {
                "id": usuario.id,
                "email": usuario.email,
                "telefone": getattr(usuario, "telefone", None)
            }
        }), 200

    except ValueError as e:
        return jsonify({"erro": str(e)}), 401
    except Exception:
        traceback.print_exc()
        return jsonify({"erro": "Erro interno no servidor."}), 500
    finally:
        db.close()