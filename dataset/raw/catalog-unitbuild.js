var script = $('#'+authorizedReadUnitId);
if (script.attr('queryData')) {
	var cmsUrl = script.attr('url');
	var scriptId = script.attr('id');
	var idRandom = 'authorizedRead_' + scriptId;
//	script.before('<div id="' + idRandom + '"></div>');
	var queryData = JSON.parse(script.attr('queryData').replace(/'/g, "\""));
	var bln = false;
	var value = '';
	if ((typeof paramsMap) != 'undefined') {
		for (i = 0; i < paramsMap.length; i++) {
			if (paramsMap[i].key == queryData.tagId){
				bln = true;
				value = paramsMap[i].value;
			}
		}
	}
	const searchValue = onLoadCustomSearch();
    let mergedObj = {};
    if (typeof searchValue === 'object' && Object.keys(searchValue).length === 0) {
    	mergedObj = value;
    } else {
    	mergedObj = searchValue;
    }
    if (typeof value === 'object') {
        for (var prop in searchValue) {
            if (searchValue.hasOwnProperty(prop)) {
                mergedObj[prop] = searchValue[prop];
            }
        }
        for (var prop in value) {
            if (value.hasOwnProperty(prop)) {
                mergedObj[prop] = value[prop];
            }
        }
    }
    var paramJson;
    if (typeof mergedObj === 'object' && Object.keys(mergedObj).length !== 0) {
        paramJson = {
            search: JSON.stringify(mergedObj)
        }
    } else {
        paramJson = {}
    }
    if (bln) {
       paramJson['pageNo'] = 99999
       paramJson['pageSize'] = 99999
    }
    if (queryData.unitType && queryData.unitType === 'ajax-xxgk' && getUrlParam('number')){
    	paramJson['pageNo'] = 1
    	paramJson['pageSize'] = 5
    	const search = {}
    	search['xxgkId'] = getUrlParam('number')
    	search['xxgkType'] = 'xxgk_combination'
    	search['className'] = ''
    	paramJson['search'] = JSON.stringify(search)
    }
    if(Object.keys(paramJson).length !== 0){
        queryData.paramJson = JSON.stringify(paramJson);
    }
    getHtml(cmsUrl, queryData, script);
}

function getHtml(url, queryData, script1) {
	$.ajax({
		url: url,
		type: 'get',
		data: queryData,
		success: function(result) {
//			$('#' + idRandom).html(result.data.html);
			script1.before(result.data.html);
			if (getUrlParam('number') && window.loadXxgkAjaxPage){
				search = {
					xxgkId:getUrlParam('number'),
			    	xxgkType:'xxgk_combination',
			    	className:''
				}
				if ($('.label-className').length === 1) {
                	loadXxgkAjaxPage($('#tree-ajax-combination .xxgkParams').attr('unitid'))
                }
			}
			// 简繁体使用
			if (isOpenTran()) {
			    zh_tranBody();
			}
		},
		error: function(error) {
			// layer.msg('系统错误');
		}
	})
}

/* 获取url中的参数 */
function getUrlParam(name) {
	var reg = new RegExp("(^|&)" + name + "=([^&]*)(&|$)"); //构造一个含有目标参数的正则表达式对象
	var r = window.location.search.substr(1).match(reg); //匹配目标参数
	if (r != null) return unescape(r[2]); return null; //返回参数值
}

// 获取cookie中数据
function getCookie(a) {
    var b = a + "=";
    if (document.cookie.length > 0) {
        offset = document.cookie.indexOf(b);
        if (offset != -1) {
            offset += b.length;
            end = document.cookie.indexOf(";", offset);
            if (end == -1) {
                end = document.cookie.length
            }
            return unescape(document.cookie.substring(offset, end))
        } else {
            return ""
        }
    }
}
// 判断是否开启简繁体
function isOpenTran() {
  if (typeof String.prototype.tran === 'function') {
	  var a = $("meta[name=WebId]").attr('content');
	  var choose = getCookie("zh_choose_" + a)
	  if (choose && choose !== 'n') {
		  return true;
	  }
  }
  return false;
}
// 处理定制查询参数
function onLoadCustomSearch() {
  let searchValue = {};
  try {
    var searchId = getQueryString('searchVal');
    if (searchId && localStorage.getItem(searchId + '_ls')) {
      sessionStorage.setItem('ss_SearchValue', localStorage.getItem(searchId + '_ls'));
    }
    if (sessionStorage.getItem('ss_SearchValue')) {
  	    window.ss_SearchValue = JSON.parse(sessionStorage.getItem('ss_SearchValue'))
  	    searchValue = window.ss_SearchValue.searchVal;
    }
  } catch (error) {}
  return searchValue;
}

// 获取url中参数
function getQueryString(name) {
  var reg = new RegExp('(^|&)' + name + '=([^&]*)(&|$)', 'i')
  var r = window.location.search.substr(1).match(reg)
  if (r != null) {
    return decodeURIComponent(r[2])
  }
  return null
}
