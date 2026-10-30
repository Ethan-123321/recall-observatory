function getQueryString(name) {
    var reg = new RegExp('(^|&)' + name + '=([^&]*)(&|$)', 'i')
    var r = window.location.search.substr(1).match(reg)
    if (r != null) {
        return decodeURIComponent(r[2])
    }
    return null
}

var isLoading = false

function loadNextPage(formId) {
    if (isLoading) return
    isLoading = true
    var elemId = formId.slice(0, -7)
    var query = window[elemId + '_queryData']
    window[elemId + '_pageParam'].pageNo++
    var pageParam = window[elemId + '_pageParam']
    pageParam.pageSize = pageParam.pageSize || pageParam.rows
    if (pageParam.count <= (pageParam.pageNo - 1) * pageParam.pageSize) {
        isLoading = false
        return
    }
    query.paramJson = JSON.stringify({
        pageNo: pageParam.pageNo,
        pageSize: pageParam.pageSize,
        loadEnabled: true,
        search: JSON.stringify(window[elemId + '_search'] || {})
    })

    $.ajax({
        url: query.unitUrl,
        type: 'get',
        async: false,
        data: query,
        success: function (result) {
            if (result.success) {
                isLoading = false
                checkAndLoadNextPage()
                if ($(result.data.html)) {
                    if (result.data.html.indexOf('<table') !== -1) {
                        var tbodyHtml = $(result.data.html).find('tbody').html()
                        tbodyHtml = tbodyHtml.replace(/<tr class="list-head">[\s\S]*?<\/tr>/g, '')
                        $('#' + formId + ' .page-content table tbody').append(
                            tbodyHtml
                        )
                    } else if (result.data.html.indexOf('card-water-fall') !== -1) {
                        $('#' + formId + ' .card-water-fall').append(
                            $(result.data.html)
                                .find('.page-content')
                                .html()
                        )
                        masonry.runOnImageLoad(function () {
                            masonry.recalculate(true)
                        }, true)
                    } else {
                        $('#' + formId + ' .page-content').append(
                            $(result.data.html)
                                .find('.page-content')
                                .html()
                        )
                    }
                }
            }
        }
    })
}

function checkAndLoadNextPage(formId) {
    const pageHeight = document.documentElement.scrollHeight
    const windowHeight = window.innerHeight

    // 如果页面高度小于等于窗口高度，说明没有滚动条
    if (pageHeight <= windowHeight) {
        loadNextPage(formId)
    }
}

function doLayPageRender(formId, queryData, pageParam, beLoadNext) {
    var elemId = formId.slice(0, -7)
    window[elemId + '_pageParam'] = pageParam
    window[elemId + '_queryData'] = queryData
    var paramJson = {
        pageNo: pageParam.pageNo,
        pageSize: pageParam.pageSize,
        loadEnabled: true,
        search: JSON.stringify(window[elemId + '_search'] || {})
    }

    if (window.ss_SearchValue) {
        var pageInfo = window.ss_SearchValue.pageInfo
        var allSearchTxt = {
            dataSources: pageInfo.dataSources,
            linkSource: pageInfo.linkSource,
            pageId: pageInfo.pageId
        }
        for (var key in window[elemId + '_search']) {
            allSearchTxt[key] = window[elemId + '_search'][key]
        }
        paramJson.search = JSON.stringify(allSearchTxt)
    }
    window[elemId + '_queryData'].paramJson = JSON.stringify(paramJson)
    if (beLoadNext) {
        checkAndLoadNextPage(formId)
        window.addEventListener('scroll', function () {
            const scrollPosition = window.innerHeight + window.scrollY
            const pageHeight = document.documentElement.scrollHeight

            if (scrollPosition >= pageHeight - 300) {
                loadNextPage(formId)
            }
        })
        return
    }
    layui.use('laypage', function () {
        var laypage = layui.laypage
        if (pageParam.count > 0) {
            $('#' + elemId + '_pagination').show()
            laypage.render({
                elem: elemId + '_pagination',
                count: +pageParam.count,
                limit: +pageParam.rows,
                curr: +pageParam.pageNo,
                jump: function (obj, first) {
                    if (!first) {
                        var paramJson = {
                            pageNo: obj.curr,
                            pageSize: obj.limit,
                            loadEnabled: true,
                            search: JSON.stringify(window[elemId + '_search'] || {})
                        }
                        if (window.ss_SearchValue) {
                            var pageInfo = window.ss_SearchValue.pageInfo
                            var allSearchTxt = {
                                dataSources: pageInfo.dataSources,
                                linkSource: pageInfo.linkSource,
                                pageId: pageInfo.pageId
                            }
                            for (var key in window[elemId + '_search']) {
                                allSearchTxt[key] = window[elemId + '_search'][key]
                            }
                            paramJson.search = JSON.stringify(allSearchTxt)
                        }
                        window[elemId + '_queryData'].paramJson = queryData.paramJson = JSON.stringify(paramJson)
                        loadSearchContent(formId, false)
                    }
                }
            })
        } else {
            $('#' + elemId + '_pagination').hide()
            $('#' + formId + ' .page-content').html('<div class="page-none" style="text-align: center;font-size: 22px;color: gray;">暂无数据</div>')
        }
    })
}

function loadSearchContent(formId, beRerenderPage) {
    var elemId = formId.slice(0, -7)
    var paramJson = JSON.parse(window[elemId + '_queryData'].paramJson)
    if (beRerenderPage) {
        paramJson.pageNo = 1
        paramJson.pageSize = window[elemId + '_pageParam'].rows
    }
    paramJson.search = JSON.stringify(window[elemId + '_search'] || {})
    window[elemId + '_queryData'].paramJson = JSON.stringify(paramJson)
    $.ajax({
        url: window[elemId + '_queryData'].unitUrl,
        type: 'get',
        async: false,
        data: window[elemId + '_queryData'],
        success: function (result) {
            if (result.success) {
                if ($(result.data.html)) {
                    if (result.data.html.indexOf('card-water-fall') !== -1) {
                        $('#' + formId + ' .card-water-fall').html(
                            $(result.data.html)
                                .find('.page-content')
                                .html()
                        )
                        masonry.runOnImageLoad(function () {
                            masonry.recalculate(true)
                        }, true)
                        window[elemId + '_pageParam'].pageNo = 1
                    } else {
                        $('#' + formId + ' .page-content').html(
                            $(result.data.html)
                                .find('.page-content')
                                .html()
                        )
                    }
                }
                if (beRerenderPage && ((typeof window.needPagination !== 'boolean') || !!window.needPagination)) {
                    var dom = $(result.data.html).find('#' + elemId + '_pagination')
                    if (dom && dom.attr('queryData')) {
                        var pageParam = dom.attr('queryData')
                        pageParam = pageParam.replace(/\'/g, '"')
                        pageParam = JSON.parse(pageParam)
                        pageParam.pageNo = 1
                        doLayPageRender(formId, window[elemId + '_queryData'], pageParam)
                    }
                }
            }
        },
        error: function (err) {
            throw err
            return false
        }
    })
}

// 获取选中radio
function getRadioCheck() {
    if (document.getElementById('correlation').checked) return 'correlation'
    if (document.getElementById('timeDesc').checked) return 'timeDesc'
    if (document.getElementById('createDateDesc').checked) return 'createDateDesc'
    return 'timeDesc'
}

// 判断有没有radio
function hasRadio() {
    if (document.getElementById('correlation') && document.getElementById('timeDesc') && document.getElementById('createDateDesc')) {
        return true
    }
    return false
}

function handleQuery(formId, data) {
    var elemId = formId.slice(0, -7)
    window[elemId + '_search'] = data.field
    // 当选中信息公开的时候添加order参数
    if (JSON.stringify(data.field) === '{}') {
        $('.tile-list').each(function (index, dom) {
            $(dom)
                .children('li')
                .eq(0)
                .addClass('on')
                .siblings()
                .removeClass('on')
        })
        $('.allchoiceDiv').each(function (index, dom) {
            $(dom).children('li').removeClass('on')
        })
        $('.tile-list1').each(function (index, dom) {
            $(dom).children('li').removeClass('on')
        })

        $('.searchdata').each(function (index, dom) {
            $(dom).remove()
        })
        this.dataArr2 = []
        this.arr = []
    }

    // 重置表单数据
    if (JSON.stringify(data.field) == '{}') {
        resetFormData(formId, elemId)
    } else {
        if (hasRadio()) {
            window[elemId + '_search'].order = getRadioCheck()
        }
    }

    if (isForwardToNewLink) {
        search2NewPage(formId, data.field)
    } else {
        loadSearchContent(formId, true)
    }
    return false
}

function search2NewPage(formId, data) {
    var elemId = formId.slice(0, -7)
    var ss_SearchValue = {
        searchVal: data,
        pageInfo: {
            dataSources: dataSources || '',
            linkSource: linkSource || '',
            pageId: currentPageId || ''
        }
    }
    var nowDate = Date.now()
        .toString()
        .slice(-6)
    localStorage.setItem(formId + nowDate + '_ls', JSON.stringify(ss_SearchValue))
    window.open(window[elemId + '_forwardUrl'] + '?searchVal=' + formId + nowDate)
}

function getSearchValue() {
    var searchId = getQueryString('searchVal')
    if (searchId && localStorage.getItem(searchId + '_ls')) {
        sessionStorage.setItem('ss_SearchValue', localStorage.getItem(searchId + '_ls'))
        localStorage.removeItem(searchId + '_ls')
    }
    if (sessionStorage.getItem('ss_SearchValue')) {
        window.ss_SearchValue = JSON.parse(sessionStorage.getItem('ss_SearchValue'))
        for (var key in window.ss_SearchValue.searchVal) {
            if ($("*[name='" + key + "']")[0].tagName.toLowerCase() === 'input') {
                $("input[name='" + key + "']").val(window.ss_SearchValue.searchVal[key])
                // 年份平铺
                if ($.find('.' + key + '_time_list').length) {
                    highlightTileListItem('.' + key + '_time_list', window.ss_SearchValue.searchVal[key].split(','))
                }
                // 其他信息公开字段平铺
                if ($.find('.' + key + '_list').length) {
                    highlightTileListItem('.' + key + '_list', window.ss_SearchValue.searchVal[key].split(','))
                }
            } else {
                $("*[name='" + key + "']")
                    .children('option')
                    .each(function () {
                        if ($(this).attr('value') === window.ss_SearchValue.searchVal[key]) {
                            $("*[name='" + key + "']")
                                .parent()
                                .find('input')
                                .parent()
                                .siblings()
                                .children()
                                .eq($(this).index())
                                .click()
                        }
                    })
            }
        }
        if (thisSettingFormId) {
            handleQuery(thisSettingFormId, {field: window.ss_SearchValue.searchVal})
        }
    }
}

function changeYear(formId, name, key) {
    var elemId = formId.slice(0, -7)
    var inputDom = $('#' + formId + ' .layui-input[name="' + name + '"]')
    if (key) {
        var dom = $('#' + formId + ' .' + name + '_time_list li[_key="' + key + '"]')
        dom.toggleClass('on')
        var val = inputDom.val()
        if (val) {
            var varArr = val.split(',')
            var varArrIndex = varArr.indexOf(key)
            if (varArrIndex !== -1) {
                varArr.splice(varArrIndex, 1)
            } else {
                varArr.push(key)
            }
            inputDom.val(varArr.join(','))
        } else {
            inputDom.val(key)
        }
        val = inputDom.val()
        if (val) {
            dom
                .parent()
                .children('li')
                .eq(0)
                .removeClass('on')
        } else {
            dom
                .parent()
                .children('li')
                .eq(0)
                .addClass('on')
        }
    } else {
        var domArr = $('#' + formId + ' .' + name + '_time_list li')
        domArr
            .eq(0)
            .addClass('on')
            .siblings()
            .removeClass('on')
        inputDom.val('')
    }
    $('#' + formId + ' .layui-input-block')
        .children()
        .eq(0)
        .trigger('click')
}

function changeData(formId, name, key) {
    var elemId = formId.slice(0, -7)
    var inputDom = $('#' + formId + ' .layui-input[name="' + name + '"]')
    if (key) {
        var dom = $('#' + formId + ' .' + name + '_list li[_key="' + key + '"]')
        dom.toggleClass('on')
        var val = inputDom.val()
        if (val) {
            var varArr = val.split(',')
            var varArrIndex = varArr.indexOf(dom.attr('_key'))
            if (varArrIndex !== -1) {
                varArr.splice(varArrIndex, 1)
            } else {
                varArr.push(dom.attr('_key'))
            }
            inputDom.val(varArr.join(','))
        } else {
            inputDom.val(dom.attr('_key'))
        }
        val = inputDom.val()
        if (val) {
            dom
                .parent()
                .children('li')
                .eq(0)
                .removeClass('on')
        } else {
            dom
                .parent()
                .children('li')
                .eq(0)
                .addClass('on')
        }
    } else {
        var domArr = $('#' + formId + ' .' + name + '_list li')
        domArr
            .eq(0)
            .addClass('on')
            .siblings()
            .removeClass('on')
        inputDom.val('')
    }
    $('#' + formId + ' .layui-input-block')
        .children()
        .eq(0)
        .trigger('click')
}

function highlightTileListItem(querySelector, needHighlightYearArr) {
    if (needHighlightYearArr.length > 0) {
        $(querySelector + ' li').eq(0).removeClass('on')
    }
    $(querySelector + ' li').each(function (index, item) {
        for (var j = 0; j < needHighlightYearArr.length; j++) {
            if ($(item).attr('_key') === needHighlightYearArr[j]) {
                $(item).addClass('on')
            }
        }
    })
}

function doRenderDropdown(key, treeData) {
    treeData = JSON.parse(treeData.replace(/#/g, '"'))
    var dom = $('.layui-dropdown div[_key="' + key + '"]')
    treeData.unshift({title: '清除已选'})
    renderLayuiTreeData('.layui-dropdown div[_key="' + key + '"]', treeData)
}

function renderLayuiTreeData(querySelector, treeData) {
    layui.use(['tree'], function () {
        var tree = layui.tree
        tree.render({
            elem: querySelector,
            data: treeData,
            showCheckbox: false,
            onlyIconControl: true,
            click: function (obj) {
                if (obj.data.title === '清除已选') {
                    $(querySelector)
                        .parent()
                        .siblings('input[type="text"]')
                        .val('')
                    $(querySelector)
                        .parent()
                        .siblings('input[type="hidden"]')
                        .val('')
                } else {
                    $(querySelector)
                        .parent()
                        .siblings('input[type="text"]')
                        .val(obj.data.title)
                    $(querySelector)
                        .parent()
                        .siblings('input[type="hidden"]')
                        .val(obj.data.key)
                }
                window.setTimeout(function () {
                    $(querySelector)
                        .parent()
                        .hide()
                })
            }
        })
    })
    layui.use(['dropdown'], function () {
        var dropdown = layui.dropdown
        dropdown.render()
    })
}

function numericalCompare(num, data) {
    if (eval(num) > eval(data)) {
        return false
    }
    return true
}

function resetFormData(formId, elemId) {
    var elems = $('#' + formId).find('input.layui-input')
    if (elems && elems.length > 0) {
        for (i = 0; i < elems.length; i++) {
            $(elems[i]).val('')
        }
    }
    if (hasRadio()) {
        window[elemId + '_search'].order = 'timeDesc'
    }
}

function treeSelect(groupData) {
    layui.use('layCascader', function () {
        var layCascader = layui.layCascader
        layCascader({
            elem: '#demo1',
            clearable: true,
            options: groupData.tranferedData,
            props: {
                multiple: true
            }
        })
    })
}

function treeSelect2(groupData) {
    layui.use('layCascader', function () {
        var layCascader = layui.layCascader
        layCascader({
            elem: '#demo2',
            clearable: true,
            options: groupData.tranferedData
        })
    })
}

function getCookie(cookieName) {
    var cookieValue = ''
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';')
        for (var i = 0; i < cookies.length; i++) {
            var cookie = cookies[i]
            if (
                cookie.substring(0, cookieName.length + 1).trim() ==
                cookieName.trim() + '='
            ) {
                cookieValue = cookie.substring(cookieName.length + 1, cookie.length)
                break
            }
        }
    }
    return cookieValue
}

function getData(id) {
    var value = $('#' + id).val()
    var token = getCookie('access-token')
    var param = {
        searchText: value,
        columnId: null,
        pageSize: 10,
        token
    }
    $.ajax({
        url: '/api-gateway/jpaas-publish-server/front/page/custom/association',
        type: 'get',
        async: false,
        data: param,
        success: function (res) {
            if (res.success) {
                if (res.data.length > 0) {
                    var list = res.data
                    var str = ''
                    for (var i in list) {
                        str += `<p style="cursor:pointer" onclick="clickitem('${list[i]}','${id}')">${list[i]}</p>`
                    }
                    $('#' + id + '-show').html(str)
                    $('#' + id + '-show').removeClass('displayNone')
                }
            }
        },
        error: function (err) {
            throw err
            return false
        }
    })
}

function clickitem(i, id) {
    $('#' + id).val(i)
    $('#' + id + '-show').addClass('displayNone')
}

var arr = []

function changeItem(i, data, all, mul, key) {
    var index = ''
    if (all === 1) {
        index = i
    } else {
        index = i - 1
    }

    if (i === 0) {
        $('#' + key).val('')
    } else {
        if (mul === 3) {
            if (this.arr.indexOf(data) === -1) {
                this.arr.push(data)
            } else {
                this.arr.forEach(function (item, j) {
                    if (item === data) {
                        this.arr.splice(j, 1)
                    }
                })
            }
            $('#' + key).val(this.arr.join(','))
        } else {
            $('#' + key).val(data)
        }
    }

    if (mul === 4) {
        $('#' + key).parent().children('li').removeClass('on')
        if ($('#' + key).parent().children('li').eq(index).hasClass('on')) {
            $('#' + key).parent().children('li').eq(index).removeClass('on')
        } else {
            $('#' + key).parent().children('li').eq(index).addClass('on')
            $('#' + key).parent().children('li').eq(index).siblings().removeClass('on')
        }
    } else {
        if ($('#' + key).parent().children('li').eq(index).hasClass('on')) {
            $('#' + key).parent().children('li').eq(index).removeClass('on')
        } else {
            if ($('#' + key).parent().children('li').eq(index)[0].innerHTML === '全部') {
                $('#' + key).parent().children('li').eq(index).siblings().removeClass('on')
            } else {
                if ($('#allchoice') && $('#allchoice').hasClass('on')) {
                    $('#allchoice').removeClass('on')
                }
            }
            $('#' + key).parent().children('li').eq(index).addClass('on')
        }
    }
}

var dataArr2 = []

function changeItems(it, title, key, label, id) {
    var yy = true
    var flag = true

    if (dataArr2.length > 0) {
        dataArr2.forEach(function (item) {
            if (item.name === key) {
                yy = false
            }
        })
    }

    if (yy) {
        dataArr2.forEach(function (item) {
            if (item.name === key) {
                item.ids.forEach(function (ele) {
                    if (ele === id) {
                        flag = false
                    }
                })
            }
        })
        if (flag) {
            it.parent().parent().children(':first').append(`<div id='searchdata' class="searchdata">${title}:${label}<img onclick="closedata($(this),'${id}','${key}','${title}')" src="/cms_files/default/script/search/close.png" class='imgIcon'></img></div>`)
        }
        dataArr2.push({
            name: key,
            ids: [id]
        })
    } else {
        var flag2 = false

        dataArr2.forEach(function (item) {
            if (item.name === key) {
                item.ids.forEach(function (i) {
                    if (i === id) {
                        flag2 = true
                    }
                })
                if (!flag2) {
                    item.ids.push(id)
                    it.parent().parent().children(':first').append(`<div id='searchdata' class="searchdata">${title}:${label}<img onclick="closedata($(this),'${id}','${key}','${title}')" src="/cms_files/default/script/search/close.png" class='imgIcon'></img></div>`)
                }
            }
        })
    }

    dataArr2.forEach(function (t) {
        if (t.name === key) {
            $('#' + key).val(t.ids.join(','))
        }
    })
    if (it.hasClass('on')) {
        it.removeClass('on')
        $('.searchData').each(function (index, dom) {
            $(dom).children('div').each(function (it, ele) {
                if (ele.innerText === title + ':' + label) {
                    ele.remove()
                }
            })
        })
        dataArr2.forEach(function (item, i) {
            item.ids.forEach(function (ele, t) {
                if (ele === id) {
                    item.ids.splice(t, 1)
                }
            })
        })
    } else {
        it.addClass('on')
    }
}

function closedata(it, id, key, title) {
    dataArr2.forEach(function (item, i) {
        item.ids.forEach(function (t, index) {
            if (t === id) {
                item.ids.splice(index, 1)
                it.parent().remove()
            }
        })
    })

    dataArr2.forEach(function (t) {
        if (t.name === key) {
            $('#' + key).val(t.ids.join(','))
        }
    })
    if ($('.tile-list1').length > 0) {
        $('.tile-list1').each(function (index, dom) {
            $(dom).children('li').each(function (i, ele) {
                if (title + ':' + ele.children[0].innerText === it.parent()[0].innerText) {
                    $(ele).removeClass('on')
                }
            })
        })
    }
}
