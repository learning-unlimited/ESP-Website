$j(function () {
  $j('#random-submit').click(function () {
    $j.get('/random/ajax', '', function (cls) {
      $j('#random-title').text(cls.title);
      $j('#random-program').text(cls.program);
      $j('#random-info').text(cls.info);
    }, "json");
  });
});
