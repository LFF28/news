"""邮件发送（尾单元）：通过 SMTP 发送 HTML 摘要到指定邮箱。"""
import datetime
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

from .base import Unit


class EmailSender(Unit):
    name = "EmailSender"

    def __init__(self, config: dict, logger):
        super().__init__(config, logger)
        email_cfg = config.get("email", {})
        self.smtp_host = email_cfg.get("smtp_host")
        self.smtp_port = email_cfg.get("smtp_port", 587)
        self.use_tls = email_cfg.get("use_tls", True)
        self.username = email_cfg.get("username")
        self.password = email_cfg.get("password")
        self.from_addr = email_cfg.get("from_addr", self.username)
        self.to_addrs = email_cfg.get("to_addrs", [])
        self.subject_template = email_cfg.get("subject", "AI News Digest {date}")

    def run(self, input_data: dict):
        html = input_data.get("html") if isinstance(input_data, dict) else None
        if not html:
            raise RuntimeError("EmailSender 未收到 HTML 内容")
        if not self.to_addrs:
            raise RuntimeError("未配置收件人 email.to_addrs")

        subject = self.subject_template.format(date=datetime.date.today().isoformat())
        msg = MIMEText(html, "html", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = formataddr((str(Header("AI News Digest", "utf-8")), self.from_addr))
        msg["To"] = ", ".join(self.to_addrs)

        self.logger.info("通过 %s:%s 发送邮件至 %s", self.smtp_host, self.smtp_port, self.to_addrs)

        if self.use_tls:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
            server.starttls()
        elif self.smtp_port == 465:
            server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)

        try:
            if self.username and self.password:
                server.login(self.username, self.password)
            server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
        finally:
            server.quit()

        self.logger.info("邮件发送成功：%s", subject)
        return None
