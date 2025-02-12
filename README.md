<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
</head>
<body>
  <h1>실행 방법</h1>
  <p>터미널에서 아래 명령어를 입력하여 서버를 실행하세요:</p>
  <pre><code>uvicorn main:app --reload --port [포트]</code></pre>
  <br>
  <p>서버가 실행되면, 웹 브라우저에서 다음 URL로 접속하여 테스트할 수 있습니다:</p>
  <p>
    <a href="http://127.0.0.1:[포트]/static/index.html" target="_blank">
      http://127.0.0.1:[포트]/static/index.html
    </a>
  </p>
</body>
</html>
