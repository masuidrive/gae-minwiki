$(document).ready(function() {
	var newWikiPages = $("#content .new-page").map(function(i, el){return $(el).attr("title");});
	var text = $("#content").text();
	converter = new Showdown.converter();
	$("#content").html(converter.makeHtml(text, newWikiPages));
});
